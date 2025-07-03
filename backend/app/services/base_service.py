"""
Base Service

Contains common functionality for all data services.
"""

from datetime import datetime, date
from typing import Any, Dict, List, Optional, Type, Union, Tuple
from sqlalchemy import and_, or_, func, desc, asc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.sql import Select

from app.core.database import get_session
from app.models.base import Base
import structlog

logger = structlog.get_logger()


class BaseService:
    """
    Base service class with common CRUD and query operations.
    
    Features:
    - Async database operations
    - Advanced filtering and search
    - Pagination with performance optimization
    - Bulk operations
    - Caching support
    - Query optimization
    """
    
    def __init__(self, model: Type[Base], session: AsyncSession = None):
        """
        Initialize base service.
        
        Args:
            model: SQLAlchemy model class
            session: Database session (optional)
        """
        self.model = model
        self._session = session
    
    @property
    async def session(self) -> AsyncSession:
        """Get database session."""
        if self._session is None:
            self._session = await get_session()
        return self._session
    
    async def close_session(self):
        """Close database session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    # CRUD Operations
    
    async def create(self, data: Dict[str, Any]) -> Base:
        """
        Create new record.
        
        Args:
            data: Record data
            
        Returns:
            Created record
        """
        session = await self.session
        
        record = self.model(**data)
        session.add(record)
        await session.commit()
        await session.refresh(record)
        
        logger.info(
            "Record created",
            model=self.model.__name__,
            record_id=getattr(record, 'id', None),
        )
        
        return record
    
    async def create_many(self, data_list: List[Dict[str, Any]]) -> List[Base]:
        """
        Create multiple records in batch.
        
        Args:
            data_list: List of record data
            
        Returns:
            List of created records
        """
        session = await self.session
        
        records = [self.model(**data) for data in data_list]
        session.add_all(records)
        await session.commit()
        
        logger.info(
            "Batch records created",
            model=self.model.__name__,
            count=len(records),
        )
        
        return records
    
    async def get_by_id(self, record_id: Any) -> Optional[Base]:
        """
        Get record by ID.
        
        Args:
            record_id: Record ID
            
        Returns:
            Record or None if not found
        """
        session = await self.session
        return await session.get(self.model, record_id)
    
    async def get_by_field(self, field: str, value: Any) -> Optional[Base]:
        """
        Get record by field value.
        
        Args:
            field: Field name
            value: Field value
            
        Returns:
            Record or None if not found
        """
        session = await self.session
        query = session.query(self.model).filter(getattr(self.model, field) == value)
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    async def update(self, record_id: Any, data: Dict[str, Any]) -> Optional[Base]:
        """
        Update record by ID.
        
        Args:
            record_id: Record ID
            data: Updated data
            
        Returns:
            Updated record or None if not found
        """
        session = await self.session
        record = await session.get(self.model, record_id)
        
        if not record:
            return None
        
        for key, value in data.items():
            if hasattr(record, key):
                setattr(record, key, value)
        
        record.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(record)
        
        logger.info(
            "Record updated",
            model=self.model.__name__,
            record_id=record_id,
        )
        
        return record
    
    async def delete(self, record_id: Any) -> bool:
        """
        Delete record by ID.
        
        Args:
            record_id: Record ID
            
        Returns:
            True if deleted, False if not found
        """
        session = await self.session
        record = await session.get(self.model, record_id)
        
        if not record:
            return False
        
        await session.delete(record)
        await session.commit()
        
        logger.info(
            "Record deleted",
            model=self.model.__name__,
            record_id=record_id,
        )
        
        return True
    
    # Query Operations
    
    async def count(self, filters: Dict[str, Any] = None) -> int:
        """
        Count records with optional filters.
        
        Args:
            filters: Filter criteria
            
        Returns:
            Record count
        """
        session = await self.session
        query = session.query(func.count(self.model.id))
        
        if filters:
            query = self._apply_filters(query, filters)
        
        result = await session.execute(query)
        return result.scalar()
    
    async def exists(self, filters: Dict[str, Any]) -> bool:
        """
        Check if records exist with given filters.
        
        Args:
            filters: Filter criteria
            
        Returns:
            True if records exist
        """
        count = await self.count(filters)
        return count > 0
    
    async def list(
        self,
        filters: Dict[str, Any] = None,
        sort_by: str = None,
        sort_order: str = "asc",
        limit: int = None,
        offset: int = None,
        include_relations: List[str] = None,
    ) -> List[Base]:
        """
        List records with filtering, sorting, and pagination.
        
        Args:
            filters: Filter criteria
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            limit: Maximum records to return
            offset: Records to skip
            include_relations: Relations to eagerly load
            
        Returns:
            List of records
        """
        session = await self.session
        query = session.query(self.model)
        
        # Apply filters
        if filters:
            query = self._apply_filters(query, filters)
        
        # Apply sorting
        if sort_by:
            sort_column = getattr(self.model, sort_by, None)
            if sort_column:
                if sort_order.lower() == "desc":
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(asc(sort_column))
        
        # Apply eager loading
        if include_relations:
            for relation in include_relations:
                if hasattr(self.model, relation):
                    query = query.options(selectinload(getattr(self.model, relation)))
        
        # Apply pagination
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def paginated_list(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Dict[str, Any] = None,
        sort_by: str = None,
        sort_order: str = "asc",
        include_relations: List[str] = None,
    ) -> Tuple[List[Base], int, int]:
        """
        Get paginated list of records.
        
        Args:
            page: Page number (1-based)
            page_size: Records per page
            filters: Filter criteria
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            include_relations: Relations to eagerly load
            
        Returns:
            Tuple of (records, total_count, total_pages)
        """
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get total count and records in parallel
        total_count = await self.count(filters)
        records = await self.list(
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=page_size,
            offset=offset,
            include_relations=include_relations,
        )
        
        # Calculate total pages
        total_pages = (total_count + page_size - 1) // page_size
        
        return records, total_count, total_pages
    
    async def search(
        self,
        search_term: str,
        search_fields: List[str],
        limit: int = 20,
        filters: Dict[str, Any] = None,
    ) -> List[Base]:
        """
        Full-text search across specified fields.
        
        Args:
            search_term: Search term
            search_fields: Fields to search in
            limit: Maximum results
            filters: Additional filters
            
        Returns:
            List of matching records
        """
        session = await self.session
        query = session.query(self.model)
        
        # Build search conditions
        search_conditions = []
        for field in search_fields:
            if hasattr(self.model, field):
                column = getattr(self.model, field)
                search_conditions.append(
                    column.ilike(f"%{search_term}%")
                )
        
        if search_conditions:
            query = query.filter(or_(*search_conditions))
        
        # Apply additional filters
        if filters:
            query = self._apply_filters(query, filters)
        
        # Apply limit
        if limit:
            query = query.limit(limit)
        
        result = await session.execute(query)
        return result.scalars().all()
    
    def _apply_filters(self, query: Select, filters: Dict[str, Any]) -> Select:
        """
        Apply filters to query.
        
        Args:
            query: SQLAlchemy query
            filters: Filter criteria
            
        Returns:
            Filtered query
        """
        for key, value in filters.items():
            if not hasattr(self.model, key):
                continue
            
            column = getattr(self.model, key)
            
            # Handle different types of filters
            if isinstance(value, dict):
                # Range filters
                if "gte" in value:
                    query = query.filter(column >= value["gte"])
                if "lte" in value:
                    query = query.filter(column <= value["lte"])
                if "gt" in value:
                    query = query.filter(column > value["gt"])
                if "lt" in value:
                    query = query.filter(column < value["lt"])
                if "in" in value:
                    query = query.filter(column.in_(value["in"]))
                if "not_in" in value:
                    query = query.filter(~column.in_(value["not_in"]))
                if "like" in value:
                    query = query.filter(column.ilike(f"%{value['like']}%"))
                if "not_null" in value and value["not_null"]:
                    query = query.filter(column.isnot(None))
                if "is_null" in value and value["is_null"]:
                    query = query.filter(column.is_(None))
            elif isinstance(value, list):
                # IN filter
                query = query.filter(column.in_(value))
            elif value is None:
                # NULL filter
                query = query.filter(column.is_(None))
            else:
                # Exact match
                query = query.filter(column == value)
        
        return query
    
    # Bulk Operations
    
    async def bulk_update(
        self,
        updates: List[Dict[str, Any]],
        id_field: str = "id"
    ) -> int:
        """
        Bulk update records.
        
        Args:
            updates: List of update data (each must contain id_field)
            id_field: Field to match records by
            
        Returns:
            Number of updated records
        """
        session = await self.session
        updated_count = 0
        
        for update_data in updates:
            if id_field not in update_data:
                continue
            
            record_id = update_data.pop(id_field)
            update_data["updated_at"] = datetime.utcnow()
            
            result = await session.execute(
                session.query(self.model)
                .filter(getattr(self.model, id_field) == record_id)
                .update(update_data)
            )
            updated_count += result.rowcount
        
        await session.commit()
        
        logger.info(
            "Bulk update completed",
            model=self.model.__name__,
            updated_count=updated_count,
        )
        
        return updated_count
    
    async def bulk_delete(self, filters: Dict[str, Any]) -> int:
        """
        Bulk delete records.
        
        Args:
            filters: Filter criteria for records to delete
            
        Returns:
            Number of deleted records
        """
        session = await self.session
        query = session.query(self.model)
        
        if filters:
            query = self._apply_filters(query, filters)
        
        result = await session.execute(query.delete())
        deleted_count = result.rowcount
        await session.commit()
        
        logger.info(
            "Bulk delete completed",
            model=self.model.__name__,
            deleted_count=deleted_count,
        )
        
        return deleted_count
    
    # Utility Methods
    
    async def get_unique_values(
        self,
        field: str,
        filters: Dict[str, Any] = None,
        limit: int = 100
    ) -> List[Any]:
        """
        Get unique values for a field.
        
        Args:
            field: Field name
            filters: Additional filters
            limit: Maximum values to return
            
        Returns:
            List of unique values
        """
        session = await self.session
        
        if not hasattr(self.model, field):
            return []
        
        column = getattr(self.model, field)
        query = session.query(column).distinct()
        
        if filters:
            query = self._apply_filters(query, filters)
        
        query = query.filter(column.isnot(None)).limit(limit)
        
        result = await session.execute(query)
        return [row[0] for row in result.fetchall()]
    
    async def aggregate(
        self,
        aggregations: Dict[str, str],
        filters: Dict[str, Any] = None,
        group_by: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform aggregations on data.
        
        Args:
            aggregations: Dict of {alias: "func(field)"} (e.g., {"total": "sum(amount)"})
            filters: Filter criteria
            group_by: Fields to group by
            
        Returns:
            List of aggregation results
        """
        session = await self.session
        
        # Build aggregation columns
        select_columns = []
        for alias, expr in aggregations.items():
            select_columns.append(text(expr).label(alias))
        
        # Add group by columns
        if group_by:
            for field in group_by:
                if hasattr(self.model, field):
                    select_columns.append(getattr(self.model, field))
        
        query = session.query(*select_columns)
        
        # Apply filters
        if filters:
            query = self._apply_filters(query, filters)
        
        # Apply grouping
        if group_by:
            group_columns = []
            for field in group_by:
                if hasattr(self.model, field):
                    group_columns.append(getattr(self.model, field))
            query = query.group_by(*group_columns)
        
        result = await session.execute(query)
        
        # Convert to list of dictionaries
        results = []
        for row in result.fetchall():
            row_dict = {}
            for i, column in enumerate(select_columns):
                key = column.key if hasattr(column, 'key') else f"col_{i}"
                row_dict[key] = row[i]
            results.append(row_dict)
        
        return results 