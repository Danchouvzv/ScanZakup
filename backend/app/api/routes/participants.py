"""
Participant endpoints.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_, or_, desc, asc

from app.core.database import get_async_session
from app.models import Participant, SubjectType
from app.schemas.participant import ParticipantOut, ParticipantDetail, ParticipantStats
from app.schemas.base import PaginatedResponse
from app.api.routes.auth import optional_user

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[ParticipantOut])
async def list_participants(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search in participant names"),
    subject_type_id: Optional[List[int]] = Query(None, description="Filter by subject type IDs"),
    organization_type: Optional[str] = Query(None, description="Filter by organization type"),
    region: Optional[str] = Query(None, description="Filter by region"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_blacklisted: Optional[bool] = Query(None, description="Filter by blacklist status"),
    sort_by: Optional[str] = Query("created_at", description="Sort field"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc, desc"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    List participants with filtering and pagination.
    """
    try:
        # Build base query
        query = select(Participant).options(
            selectinload(Participant.subject_type)
        )
        
        # Apply filters
        conditions = []
        
        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    Participant.name_ru.ilike(search_term),
                    Participant.name_kz.ilike(search_term),
                    Participant.biin.ilike(search_term)
                )
            )
        
        if subject_type_id:
            conditions.append(Participant.subject_type_id.in_(subject_type_id))
        
        if organization_type:
            conditions.append(Participant.organization_type.ilike(f"%{organization_type}%"))
        
        if region:
            conditions.append(Participant.region.ilike(f"%{region}%"))
        
        if is_active is not None:
            conditions.append(Participant.is_active == is_active)
        
        if is_blacklisted is not None:
            conditions.append(Participant.is_blacklisted == is_blacklisted)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Apply sorting
        sort_column = getattr(Participant, sort_by, Participant.created_at)
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
        participants = result.scalars().all()
        
        # Convert to response models
        items = []
        for participant in participants:
            item = ParticipantOut(
                id=participant.id,
                biin=participant.biin,
                name_ru=participant.name_ru,
                name_kz=participant.name_kz,
                subject_type_id=participant.subject_type_id,
                subject_type_name_ru=participant.subject_type.name_ru if participant.subject_type else None,
                subject_type_name_kz=participant.subject_type.name_kz if participant.subject_type else None,
                organization_type=participant.organization_type,
                system_id=participant.system_id,
                email=participant.email,
                phone=participant.phone,
                address=participant.address,
                region=participant.region,
                is_active=participant.is_active,
                is_blacklisted=participant.is_blacklisted,
                # Performance indicators (would be calculated from contracts)
                total_contracts=0,  # TODO: Calculate from contracts
                total_contract_value=0,  # TODO: Calculate from contracts
                success_rate=0.0,  # TODO: Calculate success rate
                average_contract_value=0.0,  # TODO: Calculate average
                last_contract_date=None,  # TODO: Get from contracts
                performance_score=0.0,  # TODO: Calculate performance score
                created_at=participant.created_at,
                updated_at=participant.updated_at
            )
            items.append(item)
        
        return PaginatedResponse[ParticipantOut](
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
            detail=f"Failed to retrieve participants: {str(e)}"
        )


@router.get("/{participant_id}", response_model=ParticipantDetail)
async def get_participant(
    participant_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Get detailed participant information by ID.
    """
    try:
        query = select(Participant).options(
            selectinload(Participant.subject_type)
        ).where(Participant.id == participant_id)
        
        result = await db.execute(query)
        participant = result.scalar_one_or_none()
        
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Participant not found"
            )
        
        # Build detailed response
        return ParticipantDetail(
            id=participant.id,
            biin=participant.biin,
            name_ru=participant.name_ru,
            name_kz=participant.name_kz,
            subject_type_id=participant.subject_type_id,
            subject_type_name_ru=participant.subject_type.name_ru if participant.subject_type else None,
            subject_type_name_kz=participant.subject_type.name_kz if participant.subject_type else None,
            organization_type=participant.organization_type,
            system_id=participant.system_id,
            email=participant.email,
            phone=participant.phone,
            address=participant.address,
            region=participant.region,
            is_active=participant.is_active,
            is_blacklisted=participant.is_blacklisted,
            # Detailed information
            description_ru=participant.description_ru,
            description_kz=participant.description_kz,
            registration_date=participant.registration_date,
            location_info={
                "city": participant.city,
                "region": participant.region,
                "country": "Kazakhstan"
            },
            contact_info={
                "email": participant.email,
                "phone": participant.phone,
                "website": participant.website,
                "social_media": {}  # TODO: Add social media fields
            },
            business_info={
                "organization_type": participant.organization_type,
                "industry": participant.industry,
                "size": participant.company_size,
                "founded": participant.registration_date
            },
            financial_info={
                "annual_revenue": None,  # TODO: Add financial fields
                "credit_rating": None,
                "tax_status": "active" if participant.is_active else "inactive"
            },
            # Performance metrics (would be calculated)
            total_contracts=0,
            total_contract_value=0,
            success_rate=0.0,
            average_contract_value=0.0,
            completion_rate=0.0,
            on_time_delivery_rate=0.0,
            quality_score=0.0,
            customer_satisfaction=0.0,
            last_contract_date=None,
            first_contract_date=None,
            average_contract_duration=0.0,
            performance_score=0.0,
            performance_trend="stable",
            # Contract statistics (would be calculated)
            contracts_last_year=0,
            contracts_last_month=0,
            value_last_year=0,
            value_last_month=0,
            largest_contract_value=0,
            average_bid_success_rate=0.0,
            repeat_customer_rate=0.0,
            # Compliance information
            compliance_score=100.0 if not participant.is_blacklisted else 0.0,
            violations_count=0,
            last_violation_date=None,
            certifications=[],
            licenses=[],
            # Relationship indicators
            preferred_customers=[],
            frequent_competitors=[],
            partnership_score=0.0,
            market_share=0.0,
            # Additional fields
            additional_info=participant.additional_info,
            created_at=participant.created_at,
            updated_at=participant.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve participant: {str(e)}"
        )


@router.get("/stats/summary", response_model=ParticipantStats)
async def get_participant_stats(
    subject_type_id: Optional[List[int]] = Query(None, description="Filter by subject type IDs"),
    region: Optional[str] = Query(None, description="Filter by region"),
    organization_type: Optional[str] = Query(None, description="Filter by organization type"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Get participant statistics and summary metrics.
    """
    try:
        # Base query for statistics
        base_query = select(Participant)
        
        # Apply filters
        conditions = []
        if subject_type_id:
            conditions.append(Participant.subject_type_id.in_(subject_type_id))
        if region:
            conditions.append(Participant.region.ilike(f"%{region}%"))
        if organization_type:
            conditions.append(Participant.organization_type.ilike(f"%{organization_type}%"))
        
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        # Total count
        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total_participants = count_result.scalar()
        
        # Active participants
        active_count_result = await db.execute(
            select(func.count()).select_from(
                base_query.where(Participant.is_active == True).subquery()
            )
        )
        active_participants = active_count_result.scalar()
        
        # Blacklisted participants
        blacklisted_count_result = await db.execute(
            select(func.count()).select_from(
                base_query.where(Participant.is_blacklisted == True).subquery()
            )
        )
        blacklisted_participants = blacklisted_count_result.scalar()
        
        # Distribution by subject type
        subject_type_query = select(
            Participant.subject_type_id,
            func.count(Participant.id).label('count')
        ).group_by(Participant.subject_type_id).order_by(desc('count'))
        
        if conditions:
            subject_type_query = subject_type_query.where(and_(*conditions))
        
        subject_type_result = await db.execute(subject_type_query)
        subject_type_distribution = [
            {"subject_type_id": row[0], "count": row[1]}
            for row in subject_type_result.fetchall()
        ]
        
        # Distribution by region
        region_query = select(
            Participant.region,
            func.count(Participant.id).label('count')
        ).group_by(Participant.region).order_by(desc('count')).limit(20)
        
        if conditions:
            region_query = region_query.where(and_(*conditions))
        
        region_result = await db.execute(region_query)
        regional_distribution = [
            {"region": row[0], "count": row[1]}
            for row in region_result.fetchall()
        ]
        
        return ParticipantStats(
            total_participants=total_participants,
            active_participants=active_participants,
            blacklisted_participants=blacklisted_participants,
            # Performance statistics (would be calculated from contracts)
            average_success_rate=0.0,
            average_completion_rate=0.0,
            average_performance_score=0.0,
            # Activity statistics
            new_participants_last_month=0,  # TODO: Calculate
            participants_with_contracts=0,  # TODO: Calculate from contracts
            most_active_participants=[],  # TODO: Calculate
            # Distribution statistics
            subject_type_distribution=subject_type_distribution,
            regional_distribution=regional_distribution,
            organization_type_distribution=[],  # TODO: Calculate
            # Top performers (would be calculated from contracts)
            top_performers_by_value=[],
            top_performers_by_volume=[],
            most_reliable_suppliers=[],
            # Trends (would be calculated)
            participant_growth_trend=[],
            activity_trends=[],
            performance_trends=[],
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate statistics: {str(e)}"
        )


@router.get("/search/advanced")
async def advanced_participant_search(
    query: str = Query(..., description="Search query"),
    search_fields: Optional[List[str]] = Query(None, description="Fields to search in"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Advanced participant search with multiple criteria.
    """
    try:
        # For MVP, use basic search
        search_term = f"%{query}%"
        
        search_query = select(Participant).options(
            selectinload(Participant.subject_type)
        ).where(
            or_(
                Participant.name_ru.ilike(search_term),
                Participant.name_kz.ilike(search_term),
                Participant.biin.ilike(search_term),
                Participant.email.ilike(search_term)
            )
        ).limit(20)
        
        result = await db.execute(search_query)
        participants = result.scalars().all()
        
        # Convert to search results
        results = []
        for participant in participants:
            results.append({
                "id": participant.id,
                "biin": participant.biin,
                "name_ru": participant.name_ru,
                "name_kz": participant.name_kz,
                "organization_type": participant.organization_type,
                "region": participant.region,
                "is_active": participant.is_active,
                "is_blacklisted": participant.is_blacklisted,
                "relevance_score": 1.0,  # Would calculate based on search algorithm
                "match_fields": ["name", "biin"]  # Would determine actual matching fields
            })
        
        return {
            "query": query,
            "total_results": len(results),
            "results": results,
            "search_time_ms": 0,  # Would measure actual search time
            "suggestions": []  # Would provide search suggestions
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        ) 