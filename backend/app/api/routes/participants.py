"""
Participant endpoints.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.api.routes.auth import optional_user

router = APIRouter()


@router.get("/", response_model=dict)
async def list_participants(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search participants"),
    biin: Optional[str] = Query(None, description="Filter by BIIN"),
    status: Optional[str] = Query(None, description="Filter by status"),
    sort_by: Optional[str] = Query("created_at", description="Sort field"),
    sort_order: Optional[str] = Query("desc", description="Sort order"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """List participants with filtering and pagination."""
    try:
        # Mock data for MVP
        mock_items = [
            {
                "id": 1,
                "biin": "123456789012",
                "name_ru": "ТОО Техносервис",
                "name_kz": "Техносервис ЖШС",
                "status": "active",
                "registration_date": datetime(2020, 5, 15),
                "total_contracts": 23,
                "total_value": 450000000.00,
                "success_rate": 78.5,
                "created_at": datetime(2020, 5, 15)
            },
            {
                "id": 2,
                "biin": "987654321098",
                "name_ru": "ИП Канцтовары",
                "name_kz": "Кеңсе тауарлары ЖК",
                "status": "active",
                "registration_date": datetime(2019, 8, 22),
                "total_contracts": 19,
                "total_value": 380000000.00,
                "success_rate": 65.2,
                "created_at": datetime(2019, 8, 22)
            }
        ]
        
        # Apply filtering
        filtered_items = mock_items
        
        if search:
            filtered_items = [
                item for item in filtered_items 
                if search.lower() in item["name_ru"].lower()
            ]
        
        if biin:
            filtered_items = [
                item for item in filtered_items 
                if item["biin"] == biin
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
            detail=f"Failed to retrieve participants: {str(e)}"
        )


@router.get("/{participant_id}", response_model=dict)
async def get_participant(
    participant_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """Get detailed participant information by ID."""
    try:
        if participant_id == 1:
            return {
                "id": 1,
                "biin": "123456789012",
                "name_ru": "ТОО Техносервис",
                "name_kz": "Техносервис ЖШС",
                "status": "active",
                "registration_date": datetime(2020, 5, 15),
                "address": "г. Алматы, ул. Наурызбай Батыра, 17",
                "phone": "+7 (727) 123-45-67",
                "email": "info@techservice.kz",
                "director": "Иванов Иван Иванович",
                "total_contracts": 23,
                "total_value": 450000000.00,
                "success_rate": 78.5,
                "average_contract_value": 19565217.39,
                "last_contract_date": datetime(2024, 3, 15),
                "rating": 4.2,
                "created_at": datetime(2020, 5, 15),
                "updated_at": datetime(2024, 3, 20)
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Participant not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve participant: {str(e)}"
        )


@router.get("/stats/summary", response_model=dict)
async def get_participant_stats(
    date_from: Optional[datetime] = Query(None, description="Start date"),
    date_to: Optional[datetime] = Query(None, description="End date"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """Get participant statistics and summary metrics."""
    try:
        return {
            "total_participants": 2847,
            "active_participants": 1923,
            "blacklisted_participants": 45,
            "new_this_month": 67,
            "average_success_rate": 72.3,
            "top_performers": [
                {
                    "biin": "123456789012",
                    "name": "ТОО Техносервис",
                    "success_rate": 78.5,
                    "total_value": 450000000.00
                },
                {
                    "biin": "987654321098",
                    "name": "ИП Канцтовары", 
                    "success_rate": 65.2,
                    "total_value": 380000000.00
                }
            ],
            "by_status": {
                "active": 1923,
                "inactive": 879,
                "blacklisted": 45
            },
            "by_region": {
                "astana": 512,
                "almaty": 687,
                "shymkent": 298,
                "other": 1350
            },
            "generated_at": datetime.now()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate statistics: {str(e)}"
        ) 