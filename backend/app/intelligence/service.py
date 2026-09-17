import logging
import asyncio
from typing import Any, Dict, List, Optional
from app.nlp.schemas import NLPResult
from app.nlp.service import nlp_service
from app.schemas.common import GeoJSONPoint
from app.schemas.event import EventCreate, EventResponse, EventUpdate
from app.schemas.raw_post import RawPostResponse
from app.db.repositories.event import EventRepository
from app.db.repositories.raw_post import RawPostRepository
from app.intelligence.threat_scorer import calculate_threat_score, is_post_relevant
from app.intelligence.credibility_scorer import calculate_credibility_score
from app.intelligence.clustering import find_best_matching_event
from app.core.redis import publish_event
from app.services.webhook_service import dispatch_webhooks_for_event

logger = logging.getLogger("threat_atlas.intelligence")


class IntelligenceService:
    async def process_post(
        self,
        raw_post: RawPostResponse,
        event_repo: EventRepository,
        nlp_result: Optional[NLPResult] = None,
        raw_post_repo: Optional[RawPostRepository] = None,
    ) -> Dict[str, Any]:
        """
        Processes a RawPost:
        1. Runs NLP if not supplied
        2. Searches candidate events for clustering
        3. Merges into an existing event OR creates a new event
        4. Recalculates threat & credibility scores deterministically
        5. Publishes real-time WebSocket update
        """
        # 1. Ensure NLPResult is available
        if nlp_result is None:
            nlp_result = await nlp_service.process_text(raw_post.text)

        # 2. Fetch candidate events for clustering
        from datetime import timedelta
        import math
        from app.intelligence.config import MAX_TEMPORAL_WINDOW_SECONDS, MAX_SPATIAL_DISTANCE_KM

        start_date = raw_post.original_timestamp - timedelta(seconds=MAX_TEMPORAL_WINDOW_SECONDS)
        end_date = raw_post.original_timestamp + timedelta(seconds=MAX_TEMPORAL_WINDOW_SECONDS)

        bbox = None
        if nlp_result.locations:
            primary_loc = nlp_result.locations[0]
            if primary_loc.lat != 0.0 or primary_loc.lng != 0.0:
                lat_delta = MAX_SPATIAL_DISTANCE_KM / 111.0
                cos_lat = math.cos(math.radians(primary_loc.lat))
                if cos_lat < 0.1:
                    cos_lat = 0.1
                lon_delta = MAX_SPATIAL_DISTANCE_KM / (111.0 * cos_lat)
                
                min_lon = max(-180.0, primary_loc.lng - lon_delta)
                min_lat = max(-90.0, primary_loc.lat - lat_delta)
                max_lon = min(180.0, primary_loc.lng + lon_delta)
                max_lat = min(90.0, primary_loc.lat + lat_delta)
                
                bbox = [min_lon, min_lat, max_lon, max_lat]

        candidate_events = await event_repo.list_events(
            limit=50,
            start_date=start_date,
            end_date=end_date,
            bbox=bbox
        )

        # 3. Find matching event
        match_result = find_best_matching_event(
            post_text=raw_post.text,
            post_time=raw_post.original_timestamp,
            nlp_result=nlp_result,
            candidate_events=candidate_events,
        )

        if match_result:
            matched_event, match_score = match_result
            logger.info("Merging RawPost %s into existing Event %s (score: %.4f)", raw_post.id, matched_event.id, match_score)

            # Merge raw_post_ids and source_ids
            updated_post_ids = list(set(matched_event.raw_post_ids + [raw_post.id]))
            updated_source_ids = list(set(matched_event.source_ids + [raw_post.source]))
            corroboration_count = len(updated_source_ids)

            # Merge entities
            existing_entities = matched_event.entities or {"locations": [], "organizations": [], "equipment": []}
            loc_set = set(existing_entities.get("locations", [])) | set(loc.name for loc in nlp_result.locations)
            org_set = set(existing_entities.get("organizations", [])) | set(nlp_result.organizations)
            eq_set = set(existing_entities.get("equipment", [])) | set(nlp_result.equipment)

            merged_entities = {
                "locations": list(loc_set),
                "organizations": list(org_set),
                "equipment": list(eq_set),
            }

            # Recalculate scores
            threat_score, threat_level, threat_breakdown = calculate_threat_score(
                nlp_result=nlp_result,
                corroboration_count=corroboration_count,
            )
            credibility_score, cred_breakdown = calculate_credibility_score(
                source_ids=updated_source_ids,
            )

            # Update event in DB
            event_update = EventUpdate(
                raw_post_ids=updated_post_ids,
                source_ids=updated_source_ids,
                entities=merged_entities,
                corroboration_count=corroboration_count,
                threat_score=threat_score,
                threat_level=threat_level,
                credibility_score=credibility_score,
                score_breakdown={
                    "threat": threat_breakdown,
                    "credibility": cred_breakdown,
                    "cluster_match_score": match_score,
                },
            )
            updated_event = await event_repo.update(matched_event.id, event_update)

            if raw_post_repo:
                await raw_post_repo.update_status(raw_post.id, "processed")

            if updated_event:
                await publish_event(updated_event.model_dump(), action="merged")

            return {
                "action": "merged",
                "event_id": matched_event.id,
                "match_score": match_score,
                "event": updated_event,
            }

        else:
            logger.info("No matching event found for RawPost %s. Creating new Event.", raw_post.id)

            # Construct Event Location
            location_name = None
            geo_location = None
            country_code = None
            if nlp_result.locations:
                primary_loc = nlp_result.locations[0]
                location_name = primary_loc.name
                country_code = primary_loc.country_code
                if primary_loc.lat != 0.0 or primary_loc.lng != 0.0:
                    # GeoJSON is [lng, lat]
                    geo_location = GeoJSONPoint(coordinates=[primary_loc.lng, primary_loc.lat])

            # Entities dict
            entities_dict = {
                "locations": [loc.name for loc in nlp_result.locations],
                "organizations": nlp_result.organizations,
                "equipment": nlp_result.equipment,
            }

            # Scores
            threat_score, threat_level, threat_breakdown = calculate_threat_score(
                nlp_result=nlp_result,
                corroboration_count=1,
            )
            credibility_score, cred_breakdown = calculate_credibility_score(
                source_ids=[raw_post.source],
            )

            # Generate short title
            event_type = nlp_result.event_types[0] if nlp_result.event_types else "Security Event"
            loc_str = f" in {location_name}" if location_name else ""
            title = f"{event_type.capitalize()}{loc_str}"
            if len(title) > 100:
                title = title[:97] + "..."

            event_create = EventCreate(
                title=title,
                summary=nlp_result.cleaned_text[:300] if nlp_result.cleaned_text else raw_post.text[:300],
                raw_post_ids=[raw_post.id],
                source_ids=[raw_post.source],
                event_type=event_type,
                entities=entities_dict,
                location_name=location_name,
                location=geo_location,
                country_code=country_code,
                event_timestamp=raw_post.original_timestamp,
                threat_score=threat_score,
                threat_level=threat_level,
                credibility_score=credibility_score,
                corroboration_count=1,
                score_breakdown={
                    "threat": threat_breakdown,
                    "credibility": cred_breakdown,
                },
            )

            created_event = await event_repo.create(event_create)

            if raw_post_repo:
                await raw_post_repo.update_status(raw_post.id, "processed")

            if created_event:
                await publish_event(created_event.model_dump(), action="created")
                asyncio.create_task(dispatch_webhooks_for_event(created_event))

            return {
                "action": "created",
                "event_id": created_event.id,
                "event": created_event,
            }


    async def process_pending_batch(self, db, limit: int = 100) -> dict:
        """
        Executes the end-to-end processing pipeline on pending RawPosts.
        Returns a dict of statistics.
        """
        from app.db.repositories.raw_post import RawPostRepository
        from app.db.repositories.event import EventRepository

        raw_post_repo = RawPostRepository(db)
        event_repo = EventRepository(db)

        pending_posts = await raw_post_repo.list_pending(limit=limit)
        stats = {
            "processed_count": 0,
            "events_created": 0,
            "events_merged": 0,
            "events_ignored": 0,
            "errors": 0,
        }

        if not pending_posts:
            return stats

        for post in pending_posts:
            try:
                nlp_result = await nlp_service.process_text(post.text)

                if not is_post_relevant(nlp_result):
                    logger.info("RawPost %s deemed irrelevant. Ignoring.", post.id)
                    await raw_post_repo.update_status(post.id, "ignored")
                    stats["events_ignored"] += 1
                    stats["processed_count"] += 1
                    continue

                result = await self.process_post(
                    raw_post=post,
                    event_repo=event_repo,
                    nlp_result=nlp_result,
                    raw_post_repo=raw_post_repo,
                )

                stats["processed_count"] += 1
                if result.get("action") == "created":
                    stats["events_created"] += 1
                elif result.get("action") == "merged":
                    stats["events_merged"] += 1

            except Exception as exc:
                logger.error("Error processing RawPost %s: %s", post.id, exc, exc_info=True)
                stats["errors"] += 1
                await raw_post_repo.update_status(post.id, "failed")

        return stats

intelligence_service = IntelligenceService()
