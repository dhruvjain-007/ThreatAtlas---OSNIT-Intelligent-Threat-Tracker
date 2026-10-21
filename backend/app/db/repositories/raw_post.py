import logging
from typing import Any, Dict, List, Optional
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.common import utc_now
from app.schemas.raw_post import RawPostCreate, RawPostInDB, RawPostResponse

logger = logging.getLogger("threat_atlas.repo.raw_post")


class RawPostRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["raw_posts"]

    async def create(self, post_in: RawPostCreate) -> Optional[RawPostResponse]:
        """Create a new raw post document. Returns None if post is a duplicate."""
        now = utc_now()
        post_db = RawPostInDB(
            **post_in.model_dump(),
            created_at=now,
            updated_at=now,
        )
        doc = post_db.model_dump(by_alias=True)

        try:
            result = await self.collection.insert_one(doc)
            doc["_id"] = result.inserted_id
            return self._to_response(doc)
        except DuplicateKeyError:
            logger.info(
                "Duplicate RawPost detected for source '%s' with source_id '%s'",
                post_in.source,
                post_in.source_specific_id,
            )
            return None

    async def get_by_id(self, post_id: str) -> Optional[RawPostResponse]:
        """Retrieve a RawPost by its string ObjectId."""
        if not ObjectId.is_valid(post_id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(post_id)})
        return self._to_response(doc) if doc else None

    async def get_by_source_and_id(self, source: str, source_specific_id: str) -> Optional[RawPostResponse]:
        """Retrieve a RawPost by source name and source-specific ID."""
        doc = await self.collection.find_one({
            "source": source,
            "source_specific_id": source_specific_id,
        })
        return self._to_response(doc) if doc else None

    async def get_by_ids(self, post_ids: List[str]) -> List[RawPostResponse]:
        """Retrieve multiple RawPosts by a list of string IDs, ObjectIds, or source_specific_ids."""
        if not post_ids:
            return []
        valid_ids = [ObjectId(pid) for pid in post_ids if ObjectId.is_valid(pid)]
        str_ids = [str(pid) for pid in post_ids if pid]
        query_clauses = [
            {"_id": {"$in": valid_ids + str_ids}},
            {"source_specific_id": {"$in": str_ids}},
        ]
        cursor = self.collection.find({"$or": query_clauses}).sort("original_timestamp", -1)
        docs = await cursor.to_list(length=max(100, len(post_ids) * 2))

        seen_ids = set()
        results = []
        for doc in docs:
            resp = self._to_response(doc)
            if resp.id not in seen_ids:
                seen_ids.add(resp.id)
                results.append(resp)
        return results

    async def list_posts(
        self,
        limit: int = 50,
        skip: int = 0,
        source: Optional[str] = None,
        processing_status: Optional[str] = None,
    ) -> List[RawPostResponse]:
        """List raw posts with optional source and status filters."""
        query: Dict[str, Any] = {}
        if source:
            query["source"] = source
        if processing_status:
            query["processing_status"] = processing_status

        cursor = (
            self.collection.find(query)
            .sort("original_timestamp", -1)
            .skip(skip)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        return [self._to_response(doc) for doc in docs]

    async def count_posts(
        self,
        source: Optional[str] = None,
        processing_status: Optional[str] = None,
    ) -> int:
        """Count total matching raw posts for query."""
        query: Dict[str, Any] = {}
        if source:
            query["source"] = source
        if processing_status:
            query["processing_status"] = processing_status
        return await self.collection.count_documents(query)

    async def list_pending(self, limit: int = 100) -> List[RawPostResponse]:
        """Retrieve RawPosts where processing_status == 'pending'."""
        return await self.list_posts(limit=limit, skip=0, processing_status="pending")

    async def update_status(self, post_id: str, status: str) -> bool:
        """Update processing status of a RawPost."""
        if not ObjectId.is_valid(post_id):
            return False
        result = await self.collection.update_one(
            {"_id": ObjectId(post_id)},
            {
                "$set": {
                    "processing_status": status,
                    "updated_at": utc_now(),
                }
            },
        )
        return result.modified_count > 0

    @staticmethod
    def _to_response(doc: dict) -> RawPostResponse:
        """Convert MongoDB document dict to RawPostResponse Pydantic model."""
        doc_copy = dict(doc)
        doc_copy["id"] = str(doc_copy.pop("_id"))
        return RawPostResponse(**doc_copy)
