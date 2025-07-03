"""
Lot endpoints.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_, or_, desc, asc

from app.core.database import get_async_session
from app.models import Lot, Procurement, Status
from app.schemas.lot import LotOut, LotDetail, LotFilter
from app.schemas.base import PaginatedResponse
from app.api.routes.auth import optional_user

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[LotOut])
async def list_lots(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search in lot names and descriptions"),
    procurement_id: Optional[int] = Query(None, description="Filter by procurement ID"),
    status_id: Optional[List[int]] = Query(None, description="Filter by status IDs"),
    sum_from: Optional[float] = Query(None, description="Minimum sum filter"),
    sum_to: Optional[float] = Query(None, description="Maximum sum filter"),
    quantity_from: Optional[float] = Query(None, description="Minimum quantity filter"),
    quantity_to: Optional[float] = Query(None, description="Maximum quantity filter"),
    unit: Optional[str] = Query(None, description="Filter by unit"),
    sort_by: Optional[str] = Query("created_at", description="Sort field"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc, desc"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    List lots with filtering and pagination.
    """
    try:
        # Build base query
        query = select(Lot).options(
            selectinload(Lot.procurement),
            selectinload(Lot.status)
        )
        
        # Apply filters
        conditions = []
        
        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    Lot.name_ru.ilike(search_term),
                    Lot.name_kz.ilike(search_term),
                    Lot.description_ru.ilike(search_term),
                    Lot.description_kz.ilike(search_term)
                )
            )
        
        if procurement_id:
            conditions.append(Lot.procurement_id == procurement_id)
        
        if status_id:
            conditions.append(Lot.status_id.in_(status_id))
        
        if sum_from:
            conditions.append(Lot.sum >= sum_from)
        
        if sum_to:
            conditions.append(Lot.sum <= sum_to)
        
        if quantity_from:
            conditions.append(Lot.quantity >= quantity_from)
        
        if quantity_to:
            conditions.append(Lot.quantity <= quantity_to)
        
        if unit:
            conditions.append(Lot.unit.ilike(f"%{unit}%"))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Apply sorting
        sort_column = getattr(Lot, sort_by, Lot.created_at)
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
        lots = result.scalars().all()
        
        # Convert to response models
        items = []
        for lot in lots:
            item = LotOut(
                id=lot.id,
                name_ru=lot.name_ru,
                name_kz=lot.name_kz,
                description_ru=lot.description_ru[:200] + "..." if lot.description_ru and len(lot.description_ru) > 200 else lot.description_ru,
                description_kz=lot.description_kz[:200] + "..." if lot.description_kz and len(lot.description_kz) > 200 else lot.description_kz,
                procurement_id=lot.procurement_id,
                procurement_name_ru=lot.procurement.name_ru if lot.procurement else None,
                procurement_name_kz=lot.procurement.name_kz if lot.procurement else None,
                status_id=lot.status_id,
                status_name_ru=lot.status.name_ru if lot.status else None,
                status_name_kz=lot.status.name_kz if lot.status else None,
                sum=lot.sum,
                quantity=lot.quantity,
                unit=lot.unit,
                created_at=lot.created_at,
                updated_at=lot.updated_at
            )
            items.append(item)
        
        return PaginatedResponse[LotOut](
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
            detail=f"Failed to retrieve lots: {str(e)}"
        )


@router.get("/{lot_id}", response_model=LotDetail)
async def get_lot(
    lot_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Get detailed lot information by ID.
    """
    try:
        query = select(Lot).options(
            selectinload(Lot.procurement).selectinload(Procurement.customer),
            selectinload(Lot.status)
        ).where(Lot.id == lot_id)
        
        result = await db.execute(query)
        lot = result.scalar_one_or_none()
        
        if not lot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lot not found"
            )
        
        # Build detailed response
        return LotDetail(
            id=lot.id,
            name_ru=lot.name_ru,
            name_kz=lot.name_kz,
            description_ru=lot.description_ru,
            description_kz=lot.description_kz,
            procurement_id=lot.procurement_id,
            procurement_name_ru=lot.procurement.name_ru if lot.procurement else None,
            procurement_name_kz=lot.procurement.name_kz if lot.procurement else None,
            procurement_info={
                "customer_name_ru": lot.procurement.customer.name_ru if lot.procurement and lot.procurement.customer else None,
                "customer_name_kz": lot.procurement.customer.name_kz if lot.procurement and lot.procurement.customer else None,
                "start_date": lot.procurement.start_date if lot.procurement else None,
                "end_date": lot.procurement.end_date if lot.procurement else None,
            } if lot.procurement else None,
            status_id=lot.status_id,
            status_name_ru=lot.status.name_ru if lot.status else None,
            status_name_kz=lot.status.name_kz if lot.status else None,
            sum=lot.sum,
            quantity=lot.quantity,
            unit=lot.unit,
            specifications=lot.specifications,
            additional_info=lot.additional_info,
            created_at=lot.created_at,
            updated_at=lot.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve lot: {str(e)}"
        )


@router.get("/stats/summary")
async def get_lot_stats(
    procurement_id: Optional[int] = Query(None, description="Filter by procurement ID"),
    date_from: Optional[datetime] = Query(None, description="Start date for statistics"),
    date_to: Optional[datetime] = Query(None, description="End date for statistics"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Get lot statistics and summary metrics.
    """
    try:
        # Base query for statistics
        base_query = select(Lot)
        
        # Apply filters
        conditions = []
        if procurement_id:
            conditions.append(Lot.procurement_id == procurement_id)
        if date_from:
            conditions.append(Lot.created_at >= date_from)
        if date_to:
            conditions.append(Lot.created_at <= date_to)
        
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        # Total count
        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total_lots = count_result.scalar()
        
        # Total value
        sum_result = await db.execute(
            select(func.sum(Lot.sum)).select_from(base_query.subquery())
        )
        total_value = sum_result.scalar() or 0
        
        # Average value
        avg_result = await db.execute(
            select(func.avg(Lot.sum)).select_from(base_query.subquery())
        )
        average_value = float(avg_result.scalar() or 0)
        
        # Most common units
        units_query = select(
            Lot.unit,
            func.count(Lot.id).label('count')
        ).group_by(Lot.unit).order_by(desc('count')).limit(10)
        
        if conditions:
            units_query = units_query.where(and_(*conditions))
        
        units_result = await db.execute(units_query)
        common_units = [
            {"unit": row[0], "count": row[1]}
            for row in units_result.fetchall()
        ]
        
        return {
            "total_lots": total_lots,
            "total_value": total_value,
            "average_value": average_value,
            "common_units": common_units,
            "generated_at": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate statistics: {str(e)}"
        ) 