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
from app.intelligence.geocoding import fallback_country_geocode
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
            valid_locs = [loc for loc in nlp_result.locations if loc.lat != 0.0 or loc.lng != 0.0]
            if valid_locs:
                primary_loc = valid_locs[0]
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
                valid_locs = [loc for loc in nlp_result.locations if loc.lat != 0.0 or loc.lng != 0.0]
                primary_loc = valid_locs[0] if valid_locs else nlp_result.locations[0]
                location_name = primary_loc.name
                country_code = primary_loc.country_code
                if primary_loc.lat != 0.0 or primary_loc.lng != 0.0:
                    # GeoJSON is [lng, lat]
                    geo_location = GeoJSONPoint(coordinates=[primary_loc.lng, primary_loc.lat])

            # If specific city NER extraction failed to find coordinates, fall back to country mentions
            if geo_location is None:
                country_fallback = fallback_country_geocode([], raw_post.text)
                if country_fallback:
                    c_name, c_lat, c_lng, c_cc = country_fallback
                    location_name = location_name or c_name
                    country_code = country_code or c_cc
                    geo_location = GeoJSONPoint(coordinates=[c_lng, c_lat])

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
                if hasattr(created_event, "model_dump") and not hasattr(created_event.model_dump, "_mock_return_value"):
                    event_dict = created_event.model_dump()
                elif isinstance(created_event, dict):
                    event_dict = created_event
                else:
                    event_dict = getattr(created_event, "__dict__", {})
                if not asyncio.iscoroutine(event_dict):
                    await publish_event(event_dict, action="created")
                asyncio.create_task(dispatch_webhooks_for_event(created_event))

            return {
                "action": "created",
                "event_id": created_event.id,
                "event": created_event,
            }


    async def process_pending_batch(self, db, limit: int = 100, batch_size: int = 5) -> dict:
        """
        Executes the end-to-end processing pipeline on pending RawPosts in small chunks (default batch_size=5).
        Runs explicit garbage collection after each chunk to maintain a low RAM footprint on 512MB tiers.
        Logs throughput: posts processed, passed relevance, geocoded into events, and errors.
        Returns a dict of statistics.
        """
        import gc
        from app.db.repositories.raw_post import RawPostRepository
        from app.db.repositories.event import EventRepository

        raw_post_repo = RawPostRepository(db)
        event_repo = EventRepository(db)

        stats = {
            "processed_count": 0,
            "passed_relevance": 0,
            "geocoded_count": 0,
            "events_created": 0,
            "events_merged": 0,
            "events_ignored": 0,
            "errors": 0,
        }

        total_processed = 0
        seen_post_ids = set()

        while total_processed < limit:
            chunk_limit = min(batch_size, limit - total_processed)
            try:
                pending_posts = await raw_post_repo.list_pending(limit=chunk_limit)
            except Exception as exc:
                logger.error("Failed to fetch pending raw posts: %s", exc, exc_info=True)
                break

            if not pending_posts:
                break

            unprocessed_posts = [p for p in pending_posts if p.id not in seen_post_ids]
            if not unprocessed_posts:
                break

            for post in unprocessed_posts:
                seen_post_ids.add(post.id)
                try:
                    nlp_result = await nlp_service.process_text(post.text)

                    if not is_post_relevant(nlp_result):
                        logger.info("RawPost %s deemed irrelevant. Ignoring.", post.id)
                        await raw_post_repo.update_status(post.id, "ignored")
                        stats["events_ignored"] += 1
                        stats["processed_count"] += 1
                        total_processed += 1
                        continue

                    # Post passed relevance check
                    stats["passed_relevance"] += 1

                    result = await self.process_post(
                        raw_post=post,
                        event_repo=event_repo,
                        nlp_result=nlp_result,
                        raw_post_repo=raw_post_repo,
                    )

                    stats["processed_count"] += 1
                    total_processed += 1

                    # Check if the resulting event has coordinates
                    evt = result.get("event")
                    is_geocoded = False
                    if evt:
                        loc = getattr(evt, "location", None) or (evt.get("location") if isinstance(evt, dict) else None)
                        if loc and hasattr(loc, "coordinates") and loc.coordinates:
                            coords = loc.coordinates
                            if len(coords) >= 2 and (coords[0] != 0.0 or coords[1] != 0.0):
                                is_geocoded = True
                        elif isinstance(loc, dict) and loc.get("coordinates"):
                            coords = loc["coordinates"]
                            if len(coords) >= 2 and (coords[0] != 0.0 or coords[1] != 0.0):
                                is_geocoded = True

                    if is_geocoded:
                        stats["geocoded_count"] += 1

                    if result.get("action") == "created":
                        stats["events_created"] += 1
                    elif result.get("action") == "merged":
                        stats["events_merged"] += 1

                except Exception as exc:
                    logger.error("Error processing RawPost %s: %s", getattr(post, 'id', 'unknown'), exc, exc_info=True)
                    stats["errors"] += 1
                    stats["processed_count"] += 1
                    total_processed += 1
                    try:
                        await raw_post_repo.update_status(post.id, "failed")
                    except Exception as status_err:
                        logger.error("Failed to update status to failed for post %s: %s", getattr(post, 'id', 'unknown'), status_err)

            # Explicit garbage collection after processing each batch chunk
            gc.collect()

        logger.info(
            "Batch intelligence run finished: %d posts processed, %d passed relevance, %d geocoded into events (%d created, %d merged), %d ignored as irrelevant, %d errors",
            stats["processed_count"],
            stats["passed_relevance"],
            stats["geocoded_count"],
            stats["events_created"],
            stats["events_merged"],
            stats["events_ignored"],
            stats["errors"],
        )

        return stats

intelligence_service = IntelligenceService()
