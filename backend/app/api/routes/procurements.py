"""
Procurement endpoints.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_, or_, desc, asc

from app.core.database import get_async_session
from app.models import Procurement, Status, Customer, TradeType, SubjectType
from app.schemas.procurement import (
    ProcurementOut,
    ProcurementDetail,
    ProcurementFilter,
    ProcurementStats
)
from app.schemas.base import PaginatedResponse
from app.api.routes.auth import optional_user, require_permission
from app.services.procurement_service import ProcurementService

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[ProcurementOut])
async def list_procurements(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search in titles and descriptions"),
    status_id: Optional[List[int]] = Query(None, description="Filter by status IDs"),
    customer_bin: Optional[str] = Query(None, description="Filter by customer BIN"),
    trade_type_id: Optional[List[int]] = Query(None, description="Filter by trade type IDs"),
    subject_type_id: Optional[List[int]] = Query(None, description="Filter by subject type IDs"),
    region: Optional[str] = Query(None, description="Filter by region"),
    date_from: Optional[datetime] = Query(None, description="Filter by start date"),
    date_to: Optional[datetime] = Query(None, description="Filter by end date"),
    value_from: Optional[float] = Query(None, description="Minimum value filter"),
    value_to: Optional[float] = Query(None, description="Maximum value filter"),
    sort_by: Optional[str] = Query("created_at", description="Sort field"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc, desc"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    List procurements with filtering and pagination.
    
    Supports comprehensive filtering, searching, and sorting.
    Public endpoint with optional authentication for enhanced features.
    """
    try:
        # Build base query
        query = select(Procurement).options(
            selectinload(Procurement.status),
            selectinload(Procurement.customer),
            selectinload(Procurement.trade_type),
            selectinload(Procurement.subject_type)
        )
        
        # Apply filters
        conditions = []
        
        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    Procurement.name_ru.ilike(search_term),
                    Procurement.name_kz.ilike(search_term),
                    Procurement.description_ru.ilike(search_term),
                    Procurement.description_kz.ilike(search_term)
                )
            )
        
        if status_id:
            conditions.append(Procurement.status_id.in_(status_id))
        
        if customer_bin:
            conditions.append(Procurement.customer_bin == customer_bin)
        
        if trade_type_id:
            conditions.append(Procurement.trade_type_id.in_(trade_type_id))
        
        if subject_type_id:
            conditions.append(Procurement.subject_type_id.in_(subject_type_id))
        
        if region:
            conditions.append(Procurement.region.ilike(f"%{region}%"))
        
        if date_from:
            conditions.append(Procurement.start_date >= date_from)
        
        if date_to:
            conditions.append(Procurement.end_date <= date_to)
        
        if value_from:
            conditions.append(Procurement.total_sum >= value_from)
        
        if value_to:
            conditions.append(Procurement.total_sum <= value_to)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Apply sorting
        sort_column = getattr(Procurement, sort_by, Procurement.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Get total count
        count_query = select(func.count()).select_from(
            query.subquery()
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        # Execute query
        result = await db.execute(query)
        procurements = result.scalars().all()
        
        # Convert to response models
        items = []
        for procurement in procurements:
            item = ProcurementOut(
                id=procurement.id,
                system_id=procurement.system_id,
                name_ru=procurement.name_ru,
                name_kz=procurement.name_kz,
                description_ru=procurement.description_ru[:200] + "..." if procurement.description_ru and len(procurement.description_ru) > 200 else procurement.description_ru,
                description_kz=procurement.description_kz[:200] + "..." if procurement.description_kz and len(procurement.description_kz) > 200 else procurement.description_kz,
                customer_bin=procurement.customer_bin,
                customer_name_ru=procurement.customer.name_ru if procurement.customer else None,
                customer_name_kz=procurement.customer.name_kz if procurement.customer else None,
                trade_type_id=procurement.trade_type_id,
                trade_type_name_ru=procurement.trade_type.name_ru if procurement.trade_type else None,
                trade_type_name_kz=procurement.trade_type.name_kz if procurement.trade_type else None,
                subject_type_id=procurement.subject_type_id,
                subject_type_name_ru=procurement.subject_type.name_ru if procurement.subject_type else None,
                subject_type_name_kz=procurement.subject_type.name_kz if procurement.subject_type else None,
                status_id=procurement.status_id,
                status_name_ru=procurement.status.name_ru if procurement.status else None,
                status_name_kz=procurement.status.name_kz if procurement.status else None,
                lots_count=procurement.lots_count or 0,
                total_sum=procurement.total_sum,
                start_date=procurement.start_date,
                end_date=procurement.end_date,
                region=procurement.region,
                created_at=procurement.created_at,
                updated_at=procurement.updated_at
            )
            items.append(item)
        
        return PaginatedResponse[ProcurementOut](
            items=items,
            total=total,
            page=page,
            size=size,
            has_next=offset + size < total,
            has_prev=page > 1
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve procurements: {str(e)}"
        )


@router.get("/{procurement_id}", response_model=ProcurementDetail)
async def get_procurement(
    procurement_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Get detailed procurement information by ID.
    """
    try:
        query = select(Procurement).options(
            selectinload(Procurement.status),
            selectinload(Procurement.customer),
            selectinload(Procurement.trade_type),
            selectinload(Procurement.subject_type),
            selectinload(Procurement.lots)
        ).where(Procurement.id == procurement_id)
        
        result = await db.execute(query)
        procurement = result.scalar_one_or_none()
        
        if not procurement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Procurement not found"
            )
        
        # Build detailed response
        return ProcurementDetail(
            id=procurement.id,
            system_id=procurement.system_id,
            name_ru=procurement.name_ru,
            name_kz=procurement.name_kz,
            description_ru=procurement.description_ru,
            description_kz=procurement.description_kz,
            customer_bin=procurement.customer_bin,
            customer_name_ru=procurement.customer.name_ru if procurement.customer else None,
            customer_name_kz=procurement.customer.name_kz if procurement.customer else None,
            customer_info={
                "email": procurement.customer.email if procurement.customer else None,
                "phone": procurement.customer.phone if procurement.customer else None,
                "address": procurement.customer.address if procurement.customer else None,
            } if procurement.customer else None,
            trade_type_id=procurement.trade_type_id,
            trade_type_name_ru=procurement.trade_type.name_ru if procurement.trade_type else None,
            trade_type_name_kz=procurement.trade_type.name_kz if procurement.trade_type else None,
            subject_type_id=procurement.subject_type_id,
            subject_type_name_ru=procurement.subject_type.name_ru if procurement.subject_type else None,
            subject_type_name_kz=procurement.subject_type.name_kz if procurement.subject_type else None,
            status_id=procurement.status_id,
            status_name_ru=procurement.status.name_ru if procurement.status else None,
            status_name_kz=procurement.status.name_kz if procurement.status else None,
            lots_count=len(procurement.lots) if procurement.lots else 0,
            lots_preview=[
                {
                    "id": lot.id,
                    "name_ru": lot.name_ru,
                    "name_kz": lot.name_kz,
                    "sum": lot.sum,
                    "quantity": lot.quantity
                }
                for lot in procurement.lots[:5]  # First 5 lots
            ] if procurement.lots else [],
            total_sum=procurement.total_sum,
            start_date=procurement.start_date,
            end_date=procurement.end_date,
            region=procurement.region,
            additional_info=procurement.additional_info,
            created_at=procurement.created_at,
            updated_at=procurement.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve procurement: {str(e)}"
        )


@router.get("/stats/summary", response_model=ProcurementStats)
async def get_procurement_stats(
    date_from: Optional[datetime] = Query(None, description="Start date for statistics"),
    date_to: Optional[datetime] = Query(None, description="End date for statistics"),
    customer_bin: Optional[str] = Query(None, description="Filter by customer BIN"),
    region: Optional[str] = Query(None, description="Filter by region"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Get procurement statistics and summary metrics.
    """
    try:
        # Use procurement service for complex analytics
        service = ProcurementService(db)
        
        # Build filter parameters
        filters = {}
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        if customer_bin:
            filters['customer_bin'] = customer_bin
        if region:
            filters['region'] = region
        
        stats = await service.get_procurement_statistics(filters)
        
        return ProcurementStats(
            total_procurements=stats.get('total_procurements', 0),
            total_value=stats.get('total_value', 0),
            average_value=stats.get('average_value', 0),
            active_procurements=stats.get('active_procurements', 0),
            completed_procurements=stats.get('completed_procurements', 0),
            top_customers=stats.get('top_customers', []),
            top_regions=stats.get('top_regions', []),
            monthly_trends=stats.get('monthly_trends', []),
            status_distribution=stats.get('status_distribution', []),
            trade_type_distribution=stats.get('trade_type_distribution', []),
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate statistics: {str(e)}"
        )


@router.get("/search/advanced")
async def advanced_search(
    query: str = Query(..., description="Search query"),
    filters: Optional[str] = Query(None, description="JSON filters"),
    highlight: bool = Query(False, description="Highlight search terms"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Advanced procurement search with full-text capabilities.
    
    TODO: Implement with PostgreSQL full-text search or Elasticsearch
    """
    try:
        # For MVP, use basic ILIKE search
        # In production, implement proper full-text search
        
        search_term = f"%{query}%"
        sql_query = select(Procurement).options(
            selectinload(Procurement.status),
            selectinload(Procurement.customer),
            selectinload(Procurement.trade_type)
        ).where(
            or_(
                Procurement.name_ru.ilike(search_term),
                Procurement.name_kz.ilike(search_term),
                Procurement.description_ru.ilike(search_term),
                Procurement.description_kz.ilike(search_term)
            )
        ).limit(20)  # Limit for MVP
        
        result = await db.execute(sql_query)
        procurements = result.scalars().all()
        
        # Convert to simplified response
        items = []
        for procurement in procurements:
            item = {
                "id": procurement.id,
                "name_ru": procurement.name_ru,
                "name_kz": procurement.name_kz,
                "customer_name": procurement.customer.name_ru if procurement.customer else None,
                "total_sum": procurement.total_sum,
                "status": procurement.status.name_ru if procurement.status else None,
                "relevance_score": 1.0,  # Would calculate based on actual search algorithm
                "match_fields": ["name", "description"]  # Would determine actual matching fields
            }
            items.append(item)
        
        return {
            "query": query,
            "total_results": len(items),
            "results": items,
            "search_time_ms": 0,  # Would measure actual search time
            "suggestions": []  # Would provide search suggestions
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/{procurement_id}/lots")
async def get_procurement_lots(
    procurement_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Get lots for a specific procurement.
    """
    try:
        # First verify procurement exists
        procurement_query = select(Procurement).where(Procurement.id == procurement_id)
        procurement_result = await db.execute(procurement_query)
        procurement = procurement_result.scalar_one_or_none()
        
        if not procurement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Procurement not found"
            )
        
        # Get lots with pagination
        from app.models import Lot
        lots_query = select(Lot).where(
            Lot.procurement_id == procurement_id
        ).offset((page - 1) * size).limit(size)
        
        lots_result = await db.execute(lots_query)
        lots = lots_result.scalars().all()
        
        # Get total count
        count_query = select(func.count()).select_from(Lot).where(
            Lot.procurement_id == procurement_id
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Convert to response format
        items = []
        for lot in lots:
            items.append({
                "id": lot.id,
                "name_ru": lot.name_ru,
                "name_kz": lot.name_kz,
                "description_ru": lot.description_ru[:100] + "..." if lot.description_ru and len(lot.description_ru) > 100 else lot.description_ru,
                "sum": lot.sum,
                "quantity": lot.quantity,
                "unit": lot.unit,
                "status_id": lot.status_id,
                "created_at": lot.created_at
            })
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            has_next=(page * size) < total,
            has_prev=page > 1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve lots: {str(e)}"
        ) 