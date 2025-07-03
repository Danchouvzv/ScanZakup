"""
Contract endpoints.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.api.routes.auth import optional_user

router = APIRouter()


@router.get("/", response_model=dict)
async def list_contracts(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search in contract names"),
    procurement_id: Optional[int] = Query(None, description="Filter by procurement ID"),
    supplier_biin: Optional[str] = Query(None, description="Filter by supplier BIIN"),
    status_id: Optional[List[int]] = Query(None, description="Filter by status IDs"),
    sum_from: Optional[float] = Query(None, description="Minimum sum filter"),
    sum_to: Optional[float] = Query(None, description="Maximum sum filter"),
    date_from: Optional[datetime] = Query(None, description="Filter by start date"),
    date_to: Optional[datetime] = Query(None, description="Filter by end date"),
    sort_by: Optional[str] = Query("created_at", description="Sort field"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc, desc"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    List contracts with filtering and pagination.
    """
    try:
        # Mock data for MVP
        mock_items = [
            {
                "id": 1,
                "contract_number": "CON-2024-001",
                "procurement_id": 1,
                "supplier_biin": "123456789012",
                "supplier_name_ru": "ТОО Техносервис",
                "status_id": 1,
                "status_name_ru": "Активный",
                "sum": 5000000.00,
                "signed_date": datetime(2024, 2, 1),
                "start_date": datetime(2024, 2, 15),
                "end_date": datetime(2024, 5, 15),
                "created_at": datetime(2024, 1, 25)
            },
            {
                "id": 2,
                "contract_number": "CON-2024-002",
                "procurement_id": 2,
                "supplier_biin": "987654321098",
                "supplier_name_ru": "ИП Канцтовары",
                "status_id": 2,
                "status_name_ru": "Завершен",
                "sum": 1500000.00,
                "signed_date": datetime(2024, 1, 25),
                "start_date": datetime(2024, 2, 1),
                "end_date": datetime(2024, 3, 1),
                "created_at": datetime(2024, 1, 20)
            }
        ]
        
        # Apply filtering
        filtered_items = mock_items
        
        if search:
            filtered_items = [
                item for item in filtered_items 
                if search.lower() in item["contract_number"].lower()
            ]
        
        if supplier_biin:
            filtered_items = [
                item for item in filtered_items 
                if item["supplier_biin"] == supplier_biin
            ]
        
        if procurement_id:
            filtered_items = [
                item for item in filtered_items 
                if item["procurement_id"] == procurement_id
            ]
        
        # Pagination
        total = len(filtered_items)
        offset = (page - 1) * size
        paginated_items = filtered_items[offset:offset + size]
        
        return {
            "items": paginated_items,
            "total": total,
            "page": page,
            "size": size,
            "has_next": offset + size < total,
            "has_prev": page > 1
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve contracts: {str(e)}"
        )


@router.get("/{contract_id}", response_model=dict)
async def get_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Get detailed contract information by ID.
    """
    try:
        if contract_id == 1:
            return {
                "id": 1,
                "contract_number": "CON-2024-001",
                "procurement_id": 1,
                "procurement_name": "Поставка компьютерного оборудования",
                "supplier_biin": "123456789012",
                "supplier_name_ru": "ТОО Техносервис",
                "supplier_address": "г. Алматы, ул. Наурызбай Батыра, 17",
                "supplier_phone": "+7 (727) 123-45-67",
                "supplier_email": "info@techservice.kz",
                "status_id": 1,
                "status_name_ru": "Активный",
                "sum": 5000000.00,
                "signed_date": datetime(2024, 2, 1),
                "start_date": datetime(2024, 2, 15),
                "end_date": datetime(2024, 5, 15),
                "description_ru": "Контракт на поставку компьютерного оборудования",
                "execution_percentage": 65.0,
                "payments_made": 3250000.00,
                "penalties": 0.0,
                "created_at": datetime(2024, 1, 25),
                "updated_at": datetime(2024, 3, 10)
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve contract: {str(e)}"
        )


@router.get("/stats/summary", response_model=dict)
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
        return {
            "total_contracts": 287,
            "active_contracts": 156,
            "completed_contracts": 98,
            "cancelled_contracts": 33,
            "total_value": 4500000000.00,
            "average_value": 15679442.51,
            "executed_value": 3200000000.00,
            "execution_rate": 71.11,
            "by_status": {
                "active": 156,
                "completed": 98,
                "cancelled": 33
            },
            "by_execution": {
                "on_time": 201,
                "delayed": 45,
                "ahead": 41
            },
            "top_suppliers": [
                {
                    "biin": "123456789012",
                    "name": "ТОО Техносервис",
                    "contracts_count": 23,
                    "total_value": 450000000.00
                },
                {
                    "biin": "987654321098", 
                    "name": "ИП Канцтовары",
                    "contracts_count": 19,
                    "total_value": 380000000.00
                }
            ],
            "monthly_trends": [
                {"month": "2024-01", "count": 25, "value": 385000000},
                {"month": "2024-02", "count": 31, "value": 465000000},
                {"month": "2024-03", "count": 28, "value": 420000000}
            ],
            "generated_at": datetime.now()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate statistics: {str(e)}"
        ) 