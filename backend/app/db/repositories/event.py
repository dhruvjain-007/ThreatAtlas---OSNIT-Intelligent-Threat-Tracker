import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.common import utc_now
from app.schemas.event import EventCreate, EventInDB, EventResponse, EventUpdate, EventGlobalMetrics

logger = logging.getLogger("threat_atlas.repo.event")


class EventRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["events"]

    async def create(self, event_in: EventCreate) -> EventResponse:
        """Create a new intelligence event document."""
        now = utc_now()
        event_db = EventInDB(
            **event_in.model_dump(),
            created_at=now,
            updated_at=now,
        )
        doc = event_db.model_dump(by_alias=True)
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._to_response(doc)

    async def get_by_id(self, event_id: str) -> Optional[EventResponse]:
        """Retrieve an Event by its ObjectId or string _id."""
        query = {"$or": [{"_id": ObjectId(event_id)}, {"_id": event_id}]} if ObjectId.is_valid(event_id) else {"_id": event_id}
        doc = await self.collection.find_one(query)
        return self._to_response(doc) if doc else None

    async def update(self, event_id: str, event_update: EventUpdate) -> Optional[EventResponse]:
        """Update an existing Event document with non-None values."""
        update_data = event_update.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_by_id(event_id)

        update_data["updated_at"] = utc_now()
        query = {"$or": [{"_id": ObjectId(event_id)}, {"_id": event_id}]} if ObjectId.is_valid(event_id) else {"_id": event_id}
        result = await self.collection.find_one_and_update(
            query,
            {"$set": update_data},
            return_document=True,
        )
        return self._to_response(result) if result else None

    def _build_query(
        self,
        threat_level: Optional[str] = None,
        min_threat_score: Optional[float] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        bbox: Optional[List[float]] = None,
        search: Optional[str] = None,
        countries: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Construct MongoDB filter query from parameters."""
        query: Dict[str, Any] = {}

        if threat_level:
            query["threat_level"] = threat_level
        if min_threat_score is not None:
            query["threat_score"] = {"$gte": min_threat_score}
        if event_type:
            query["event_type"] = event_type

        # Date range filtering
        if start_date or end_date:
            time_filter: Dict[str, Any] = {}
            if start_date:
                time_filter["$gte"] = start_date
            if end_date:
                time_filter["$lte"] = end_date
            query["event_timestamp"] = time_filter

        # Geospatial Bounding Box query ($geoWithin with $box)
        if bbox and len(bbox) == 4:
            west, south, east, north = bbox
            query["location"] = {
                "$geoWithin": {
                    "$box": [
                        [west, south],
                        [east, north],
                    ]
                }
            }

        # Text search regex in title or summary
        if search:
            query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"summary": {"$regex": search, "$options": "i"}},
            ]

        if countries:
            query["country_code"] = {"$in": countries}

        return query

    async def list_events(
        self,
        limit: int = 50,
        skip: int = 0,
        threat_level: Optional[str] = None,
        min_threat_score: Optional[float] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        bbox: Optional[List[float]] = None,
        search: Optional[str] = None,
        countries: Optional[List[str]] = None,
    ) -> List[EventResponse]:
        """List events with rich filtering and pagination."""
        query = self._build_query(
            threat_level=threat_level,
            min_threat_score=min_threat_score,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
            bbox=bbox,
            search=search,
            countries=countries,
        )

        cursor = (
            self.collection.find(query)
            .sort("event_timestamp", -1)
            .skip(skip)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        return [self._to_response(doc) for doc in docs]

    async def count_events(
        self,
        threat_level: Optional[str] = None,
        min_threat_score: Optional[float] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        bbox: Optional[List[float]] = None,
        search: Optional[str] = None,
        countries: Optional[List[str]] = None,
    ) -> int:
        """Count total documents matching filters for pagination."""
        query = self._build_query(
            threat_level=threat_level,
            min_threat_score=min_threat_score,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
            bbox=bbox,
            search=search,
            countries=countries,
        )
        return await self.collection.count_documents(query)

    async def get_global_metrics(self) -> EventGlobalMetrics:
        """Calculate global counts for all threat levels using a single aggregation pipeline."""
        pipeline = [
            {
                "$group": {
                    "_id": "$threat_level",
                    "count": {"$sum": 1}
                }
            }
        ]

        cursor = self.collection.aggregate(pipeline)
        docs = await cursor.to_list(length=None)

        # Initialize counts
        total = 0
        high = 0
        medium = 0
        low = 0

        # Populate from aggregation results
        for doc in docs:
            level = doc.get("_id")
            count = doc.get("count", 0)

            total += count

            if level == "High":
                high = count
            elif level == "Medium":
                medium = count
            elif level == "Low":
                low = count

        return EventGlobalMetrics(
            total=total,
            high=high,
            medium=medium,
            low=low
        )

    async def get_distinct_countries(self) -> List[str]:
        """Get distinct country codes that exist in current events, omitting null/empty."""
        countries = await self.collection.distinct("country_code")
        return sorted([c for c in countries if c and isinstance(c, str) and c.strip()])

    @staticmethod
    def _to_response(doc: Dict[str, Any]) -> EventResponse:
        """Convert MongoDB document dict to EventResponse Pydantic model."""
        doc_copy = dict(doc)
        doc_copy["id"] = str(doc_copy.pop("_id"))
        return EventResponse(**doc_copy)
