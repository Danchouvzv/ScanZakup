"""
Procurement endpoints.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, text

from app.core.database import get_async_session
from app.models import Procurement, Lot, Contract
from app.schemas.procurement import (
    ProcurementOut,
    ProcurementDetail,
    ProcurementFilter,
    ProcurementStats
)
from app.schemas.base import PaginatedResponse
from app.api.routes.auth import optional_user

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
    
    This is a simplified version for MVP demonstration.
    In production, this would connect to real database with proper models.
    """
    try:
        # For MVP - return mock data with proper structure
        mock_items = [
            ProcurementOut(
                id=1,
                trd_buy_number_anno="REP-2024-001",
                name_ru="Поставка компьютерного оборудования",
                name_kz="Компьютерлік жабдықтарды жеткізу",
                ref_buy_status=1,
                ref_type_trade=1,
                total_sum=5000000.00,
                count_lot=3,
                ref_subject_type=1,
                customer_bin="123456789012",
                start_date=datetime(2024, 1, 15),
                end_date=datetime(2024, 2, 15),
                status_name_ru="Активный",
                customer_name_ru="Министерство образования РК",
                trade_type_name_ru="Открытый конкурс",
                lots_count=3,
                contracts_count=1,
                is_active=True,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 10)
            ),
            ProcurementOut(
                id=2,
                trd_buy_number_anno="REP-2024-002",
                name_ru="Закуп канцелярских товаров",
                name_kz="Кеңсе тауарларын сатып алу",
                ref_buy_status=2,
                ref_type_trade=2,
                total_sum=1500000.00,
                count_lot=1,
                ref_subject_type=2,
                customer_bin="987654321098",
                start_date=datetime(2024, 1, 20),
                end_date=datetime(2024, 2, 20),
                status_name_ru="Завершен",
                customer_name_ru="Акимат г. Алматы",
                trade_type_name_ru="Запрос ценовых предложений",
                lots_count=1,
                contracts_count=1,
                is_active=False,
                created_at=datetime(2024, 1, 5),
                updated_at=datetime(2024, 2, 21)
            )
        ]
        
        # Apply simple filtering
        filtered_items = mock_items
        
        if search:
            filtered_items = [
                item for item in filtered_items 
                if search.lower() in item.name_ru.lower()
            ]
        
        if customer_bin:
            filtered_items = [
                item for item in filtered_items 
                if item.customer_bin == customer_bin
            ]
        
        # Apply pagination
        total = len(filtered_items)
        offset = (page - 1) * size
        paginated_items = filtered_items[offset:offset + size]
        
        return PaginatedResponse.create(
            items=paginated_items,
            total=total,
            page=page,
            size=size
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
        # Mock detailed procurement data
        if procurement_id == 1:
            return ProcurementDetail(
                id=1,
                trd_buy_number_anno="REP-2024-001",
                name_ru="Поставка компьютерного оборудования",
                name_kz="Компьютерлік жабдықтарды жеткізу",
                ref_buy_status=1,
                ref_type_trade=1,
                total_sum=5000000.00,
                count_lot=3,
                ref_subject_type=1,
                customer_bin="123456789012",
                start_date=datetime(2024, 1, 15),
                end_date=datetime(2024, 2, 15),
                status_name_ru="Активный",
                customer_name_ru="Министерство образования РК",
                trade_type_name_ru="Открытый конкурс",
                lots_count=3,
                contracts_count=1,
                is_active=True,
                description_ru="Закуп компьютерного оборудования для образовательных учреждений",
                description_kz="Білім беру мекемелері үшін компьютерлік жабдықтарды сатып алу",
                published_date=datetime(2024, 1, 1),
                updated_date=datetime(2024, 1, 10),
                customer_name_kz="Қазақстан Республикасы Білім және ғылым министрлігі",
                customer_address="г. Астана, пр. Мангілік Ел, 8",
                customer_phone="+7 (7172) 74-26-71",
                customer_email="info@edu.gov.kz",
                total_applications=12,
                unique_suppliers=8,
                competition_level=2.67,
                participants_count=8,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 10)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Procurement not found"
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
        # Return mock statistics
        return ProcurementStats(
            total_count=156,
            period_start=date_from or datetime(2024, 1, 1),
            period_end=date_to or datetime.now(),
            total_procurements=156,
            active_procurements=45,
            completed_procurements=98,
            total_value=2500000000.00,
            average_value=16025641.03,
            median_value=8500000.00,
            procurements_this_month=23,
            procurements_this_year=156,
            by_status={
                "active": 45,
                "completed": 98,
                "cancelled": 13
            },
            by_trade_type={
                "open_tender": 89,
                "request_quotes": 45,
                "single_source": 22
            },
            by_customer_region={
                "astana": 34,
                "almaty": 28,
                "shymkent": 19,
                "other": 75
            },
            monthly_trends=[
                {"month": "2024-01", "count": 15, "value": 185000000},
                {"month": "2024-02", "count": 18, "value": 220000000},
                {"month": "2024-03", "count": 22, "value": 315000000}
            ],
            top_customers=[
                {"bin": "123456789012", "name": "Министерство образования РК", "count": 23, "value": 450000000},
                {"bin": "987654321098", "name": "Акимат г. Алматы", "count": 19, "value": 380000000}
            ],
            generated_at=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate statistics: {str(e)}"
        ) 