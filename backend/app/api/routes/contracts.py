"""
Contract endpoints.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_, or_, desc, asc

from app.core.database import get_async_session
from app.models import Contract, Procurement, Participant
from app.schemas.contract import ContractOut, ContractDetail
from app.schemas.base import PaginatedResponse
from app.api.routes.auth import optional_user

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[ContractOut])
async def list_contracts(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search in contract names"),
    procurement_id: Optional[int] = Query(None, description="Filter by procurement ID"),
    supplier_biin: Optional[str] = Query(None, description="Filter by supplier BIIN"),
    status_id: Optional[List[int]] = Query(None, description="Filter by status IDs"),
    sum_from: Optional[float] = Query(None, description="Minimum sum filter"),
    sum_to: Optional[float] = Query(None, description="Maximum sum filter"),
    date_from: Optional[datetime] = Query(None, description="Start date filter"),
    date_to: Optional[datetime] = Query(None, description="End date filter"),
    sort_by: Optional[str] = Query("created_at", description="Sort field"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc, desc"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    List contracts with filtering and pagination.
    """
    try:
        # Build base query
        query = select(Contract).options(
            selectinload(Contract.procurement),
            selectinload(Contract.supplier)
        )
        
        # Apply filters
        conditions = []
        
        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    Contract.name_ru.ilike(search_term),
                    Contract.name_kz.ilike(search_term)
                )
            )
        
        if procurement_id:
            conditions.append(Contract.procurement_id == procurement_id)
        
        if supplier_biin:
            conditions.append(Contract.supplier_biin == supplier_biin)
        
        if sum_from:
            conditions.append(Contract.sum >= sum_from)
        
        if sum_to:
            conditions.append(Contract.sum <= sum_to)
        
        if date_from:
            conditions.append(Contract.contract_date >= date_from)
        
        if date_to:
            conditions.append(Contract.contract_date <= date_to)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Apply sorting
        sort_column = getattr(Contract, sort_by, Contract.created_at)
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
        contracts = result.scalars().all()
        
        # Convert to response models
        items = []
        for contract in contracts:
            item = ContractOut(
                id=contract.id,
                name_ru=contract.name_ru,
                name_kz=contract.name_kz,
                procurement_id=contract.procurement_id,
                procurement_name_ru=contract.procurement.name_ru if contract.procurement else None,
                procurement_name_kz=contract.procurement.name_kz if contract.procurement else None,
                supplier_biin=contract.supplier_biin,
                supplier_name_ru=contract.supplier.name_ru if contract.supplier else None,
                supplier_name_kz=contract.supplier.name_kz if contract.supplier else None,
                sum=contract.sum,
                contract_date=contract.contract_date,
                completion_date=contract.completion_date,
                status_name_ru="Активный" if contract.contract_date and not contract.completion_date else "Завершен",
                status_name_kz="Белсенді" if contract.contract_date and not contract.completion_date else "Аяқталды",
                created_at=contract.created_at,
                updated_at=contract.updated_at
            )
            items.append(item)
        
        return PaginatedResponse[ContractOut](
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
            detail=f"Failed to retrieve contracts: {str(e)}"
        )


@router.get("/{contract_id}", response_model=ContractDetail)
async def get_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Get detailed contract information by ID.
    """
    try:
        query = select(Contract).options(
            selectinload(Contract.procurement),
            selectinload(Contract.supplier)
        ).where(Contract.id == contract_id)
        
        result = await db.execute(query)
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )
        
        # Build detailed response
        return ContractDetail(
            id=contract.id,
            name_ru=contract.name_ru,
            name_kz=contract.name_kz,
            procurement_id=contract.procurement_id,
            procurement_name_ru=contract.procurement.name_ru if contract.procurement else None,
            procurement_name_kz=contract.procurement.name_kz if contract.procurement else None,
            procurement_info={
                "total_sum": contract.procurement.total_sum if contract.procurement else None,
                "start_date": contract.procurement.start_date if contract.procurement else None,
                "end_date": contract.procurement.end_date if contract.procurement else None,
            } if contract.procurement else None,
            supplier_biin=contract.supplier_biin,
            supplier_name_ru=contract.supplier.name_ru if contract.supplier else None,
            supplier_name_kz=contract.supplier.name_kz if contract.supplier else None,
            supplier_info={
                "email": contract.supplier.email if contract.supplier else None,
                "phone": contract.supplier.phone if contract.supplier else None,
                "address": contract.supplier.address if contract.supplier else None,
            } if contract.supplier else None,
            sum=contract.sum,
            contract_date=contract.contract_date,
            completion_date=contract.completion_date,
            description_ru=contract.description_ru,
            description_kz=contract.description_kz,
            additional_info=contract.additional_info,
            created_at=contract.created_at,
            updated_at=contract.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve contract: {str(e)}"
        )


@router.get("/stats/summary")
async def get_contract_stats(
    supplier_biin: Optional[str] = Query(None, description="Filter by supplier BIIN"),
    date_from: Optional[datetime] = Query(None, description="Start date for statistics"),
    date_to: Optional[datetime] = Query(None, description="End date for statistics"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Get contract statistics and summary metrics.
    """
    try:
        # Base query for statistics
        base_query = select(Contract)
        
        # Apply filters
        conditions = []
        if supplier_biin:
            conditions.append(Contract.supplier_biin == supplier_biin)
        if date_from:
            conditions.append(Contract.contract_date >= date_from)
        if date_to:
            conditions.append(Contract.contract_date <= date_to)
        
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        # Total count
        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total_contracts = count_result.scalar()
        
        # Total value
        sum_result = await db.execute(
            select(func.sum(Contract.sum)).select_from(base_query.subquery())
        )
        total_value = sum_result.scalar() or 0
        
        # Average value
        avg_result = await db.execute(
            select(func.avg(Contract.sum)).select_from(base_query.subquery())
        )
        average_value = float(avg_result.scalar() or 0)
        
        # Active contracts (not completed)
        active_count_result = await db.execute(
            select(func.count()).select_from(
                base_query.where(Contract.completion_date.is_(None)).subquery()
            )
        )
        active_contracts = active_count_result.scalar()
        
        # Top suppliers
        suppliers_query = select(
            Contract.supplier_biin,
            func.count(Contract.id).label('contract_count'),
            func.sum(Contract.sum).label('total_value')
        ).group_by(Contract.supplier_biin).order_by(desc('total_value')).limit(10)
        
        if conditions:
            suppliers_query = suppliers_query.where(and_(*conditions))
        
        suppliers_result = await db.execute(suppliers_query)
        top_suppliers = [
            {
                "supplier_biin": row[0],
                "contract_count": row[1],
                "total_value": float(row[2] or 0)
            }
            for row in suppliers_result.fetchall()
        ]
        
        return {
            "total_contracts": total_contracts,
            "total_value": total_value,
            "average_value": average_value,
            "active_contracts": active_contracts,
            "completed_contracts": total_contracts - active_contracts,
            "top_suppliers": top_suppliers,
            "generated_at": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate statistics: {str(e)}"
        ) 