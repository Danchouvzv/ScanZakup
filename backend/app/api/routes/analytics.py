"""
Analytics endpoints for procurement data insights.
"""

from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, extract, cast, Date

from app.core.database import get_async_session
from app.models import Procurement, Lot, Contract, Participant
from app.schemas.analytics import (
    AnalyticsOverview,
    ProcurementAnalytics,
    MarketAnalytics,
    SupplierAnalytics,
    TrendAnalysis,
    CustomAnalyticsRequest,
    CustomAnalyticsResponse
)
from app.api.routes.auth import optional_user

router = APIRouter()


@router.get("/overview", response_model=AnalyticsOverview)
async def get_analytics_overview(
    date_from: Optional[datetime] = Query(None, description="Start date for analytics"),
    date_to: Optional[datetime] = Query(None, description="End date for analytics"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Get comprehensive analytics overview.
    """
    try:
        # Default to last 30 days if no dates provided
        if not date_from:
            date_from = datetime.utcnow() - timedelta(days=30)
        if not date_to:
            date_to = datetime.utcnow()
        
        # Base filters
        date_condition = and_(
            Procurement.published_date >= date_from,
            Procurement.published_date <= date_to
        )
        
        # Total procurements
        procurement_count_result = await db.execute(
            select(func.count(Procurement.id)).where(date_condition)
        )
        total_procurements = procurement_count_result.scalar()
        
        # Total procurement value
        procurement_value_result = await db.execute(
            select(func.coalesce(func.sum(Procurement.estimated_amount), 0)).where(date_condition)
        )
        total_procurement_value = procurement_value_result.scalar()
        
        # Active procurements
        active_procurements_result = await db.execute(
            select(func.count(Procurement.id)).where(
                and_(date_condition, Procurement.status_id == 1)  # Assuming 1 is active
            )
        )
        active_procurements = active_procurements_result.scalar()
        
        # Total lots
        lot_count_result = await db.execute(
            select(func.count(Lot.id)).join(Procurement).where(date_condition)
        )
        total_lots = lot_count_result.scalar()
        
        # Total contracts
        contract_count_result = await db.execute(
            select(func.count(Contract.id)).where(
                and_(
                    Contract.created_date >= date_from,
                    Contract.created_date <= date_to
                )
            )
        )
        total_contracts = contract_count_result.scalar()
        
        # Active suppliers
        active_suppliers_result = await db.execute(
            select(func.count(func.distinct(Contract.supplier_biin))).where(
                and_(
                    Contract.created_date >= date_from,
                    Contract.created_date <= date_to
                )
            )
        )
        active_suppliers = active_suppliers_result.scalar()
        
        # Average procurement value
        avg_procurement_value = total_procurement_value / max(total_procurements, 1)
        
        # Market competition (average lots per procurement)
        market_competition = total_lots / max(total_procurements, 1)
        
        return AnalyticsOverview(
            total_procurements=total_procurements,
            total_procurement_value=float(total_procurement_value),
            active_procurements=active_procurements,
            total_lots=total_lots,
            total_contracts=total_contracts,
            active_suppliers=active_suppliers,
            average_procurement_value=float(avg_procurement_value),
            market_competition_index=float(market_competition),
            period_from=date_from,
            period_to=date_to,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate analytics overview: {str(e)}"
        )


@router.get("/procurement", response_model=ProcurementAnalytics)
async def get_procurement_analytics(
    date_from: Optional[datetime] = Query(None, description="Start date"),
    date_to: Optional[datetime] = Query(None, description="End date"),
    customer_biin: Optional[str] = Query(None, description="Filter by customer BIIN"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Get detailed procurement analytics.
    """
    try:
        # Default date range
        if not date_from:
            date_from = datetime.utcnow() - timedelta(days=90)
        if not date_to:
            date_to = datetime.utcnow()
        
        conditions = [
            Procurement.published_date >= date_from,
            Procurement.published_date <= date_to
        ]
        
        if customer_biin:
            conditions.append(Procurement.customer_biin == customer_biin)
        
        date_condition = and_(*conditions)
        
        # Procurement trends by month
        monthly_trends_query = select(
            extract('year', Procurement.published_date).label('year'),
            extract('month', Procurement.published_date).label('month'),
            func.count(Procurement.id).label('count'),
            func.sum(Procurement.estimated_amount).label('total_value')
        ).where(date_condition).group_by('year', 'month').order_by('year', 'month')
        
        monthly_result = await db.execute(monthly_trends_query)
        procurement_trends = [
            {
                "period": f"{int(row.year)}-{int(row.month):02d}",
                "count": row.count,
                "total_value": float(row.total_value or 0),
                "average_value": float((row.total_value or 0) / max(row.count, 1))
            }
            for row in monthly_result.fetchall()
        ]
        
        # Top customers by volume
        top_customers_query = select(
            Procurement.customer_biin,
            func.count(Procurement.id).label('procurement_count'),
            func.sum(Procurement.estimated_amount).label('total_value')
        ).where(date_condition).group_by(
            Procurement.customer_biin
        ).order_by(desc('total_value')).limit(10)
        
        customers_result = await db.execute(top_customers_query)
        top_customers = [
            {
                "customer_biin": row.customer_biin,
                "procurement_count": row.procurement_count,
                "total_value": float(row.total_value or 0)
            }
            for row in customers_result.fetchall()
        ]
        
        # Method distribution
        method_distribution_query = select(
            Procurement.method_id,
            func.count(Procurement.id).label('count'),
            func.sum(Procurement.estimated_amount).label('total_value')
        ).where(date_condition).group_by(Procurement.method_id)
        
        method_result = await db.execute(method_distribution_query)
        method_distribution = [
            {
                "method_id": row.method_id,
                "count": row.count,
                "total_value": float(row.total_value or 0),
                "percentage": 0.0  # Would calculate based on total
            }
            for row in method_result.fetchall()
        ]
        
        return ProcurementAnalytics(
            procurement_trends=procurement_trends,
            top_customers_by_volume=top_customers,
            method_distribution=method_distribution,
            status_distribution=[],  # TODO: Calculate
            category_analysis=[],  # TODO: Calculate
            regional_distribution=[],  # TODO: Calculate
            value_ranges=[],  # TODO: Calculate
            success_rate_by_method={},  # TODO: Calculate
            average_duration_by_method={},  # TODO: Calculate
            period_from=date_from,
            period_to=date_to,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate procurement analytics: {str(e)}"
        )


@router.get("/market", response_model=MarketAnalytics)
async def get_market_analytics(
    date_from: Optional[datetime] = Query(None, description="Start date"),
    date_to: Optional[datetime] = Query(None, description="End date"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Get market analytics and insights.
    """
    try:
        # Default date range
        if not date_from:
            date_from = datetime.utcnow() - timedelta(days=90)
        if not date_to:
            date_to = datetime.utcnow()
        
        # Market concentration analysis
        supplier_market_share_query = select(
            Contract.supplier_biin,
            func.count(Contract.id).label('contract_count'),
            func.sum(Contract.sum).label('total_value')
        ).where(
            and_(
                Contract.created_date >= date_from,
                Contract.created_date <= date_to
            )
        ).group_by(Contract.supplier_biin).order_by(desc('total_value')).limit(20)
        
        market_result = await db.execute(supplier_market_share_query)
        market_concentration = [
            {
                "supplier_biin": row.supplier_biin,
                "contract_count": row.contract_count,
                "total_value": float(row.total_value or 0),
                "market_share": 0.0  # Would calculate based on total market
            }
            for row in market_result.fetchall()
        ]
        
        # Competition analysis
        avg_participants_query = select(
            func.avg(func.coalesce(Procurement.participants_count, 0))
        ).where(
            and_(
                Procurement.published_date >= date_from,
                Procurement.published_date <= date_to
            )
        )
        
        avg_result = await db.execute(avg_participants_query)
        average_participants = float(avg_result.scalar() or 0)
        
        return MarketAnalytics(
            market_concentration=market_concentration,
            competition_index=average_participants,
            price_trends=[],  # TODO: Calculate
            category_growth=[],  # TODO: Calculate
            regional_activity=[],  # TODO: Calculate
            new_entrants=[],  # TODO: Calculate
            market_leaders=[],  # TODO: Calculate
            seasonal_patterns=[],  # TODO: Calculate
            period_from=date_from,
            period_to=date_to,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate market analytics: {str(e)}"
        )


@router.get("/suppliers", response_model=SupplierAnalytics)
async def get_supplier_analytics(
    date_from: Optional[datetime] = Query(None, description="Start date"),
    date_to: Optional[datetime] = Query(None, description="End date"),
    top_n: int = Query(50, ge=1, le=100, description="Number of top suppliers"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Get supplier performance analytics.
    """
    try:
        # Default date range
        if not date_from:
            date_from = datetime.utcnow() - timedelta(days=180)
        if not date_to:
            date_to = datetime.utcnow()
        
        # Top performers by value
        top_suppliers_query = select(
            Contract.supplier_biin,
            func.count(Contract.id).label('contract_count'),
            func.sum(Contract.sum).label('total_value'),
            func.avg(Contract.sum).label('average_value')
        ).where(
            and_(
                Contract.created_date >= date_from,
                Contract.created_date <= date_to
            )
        ).group_by(Contract.supplier_biin).order_by(desc('total_value')).limit(top_n)
        
        suppliers_result = await db.execute(top_suppliers_query)
        top_performers = [
            {
                "supplier_biin": row.supplier_biin,
                "contract_count": row.contract_count,
                "total_value": float(row.total_value or 0),
                "average_value": float(row.average_value or 0),
                "performance_score": 100.0,  # TODO: Calculate performance score
                "reliability_score": 100.0  # TODO: Calculate reliability score
            }
            for row in suppliers_result.fetchall()
        ]
        
        return SupplierAnalytics(
            top_performers_by_value=top_performers,
            top_performers_by_volume=top_performers,  # TODO: Sort by volume
            performance_distribution=[],  # TODO: Calculate
            reliability_metrics=[],  # TODO: Calculate
            growth_analysis=[],  # TODO: Calculate
            category_specialization=[],  # TODO: Calculate
            regional_presence=[],  # TODO: Calculate
            new_suppliers=[],  # TODO: Calculate
            period_from=date_from,
            period_to=date_to,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate supplier analytics: {str(e)}"
        )


@router.get("/trends", response_model=TrendAnalysis)
async def get_trend_analysis(
    period: str = Query("quarterly", description="Period: monthly, quarterly, yearly"),
    metrics: Optional[List[str]] = Query(None, description="Metrics to analyze"),
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Get trend analysis for various metrics.
    """
    try:
        # Calculate date ranges based on period
        current_date = datetime.utcnow()
        
        if period == "monthly":
            date_from = current_date - timedelta(days=365)  # Last 12 months
            group_format = "YYYY-MM"
        elif period == "quarterly":
            date_from = current_date - timedelta(days=1095)  # Last 3 years
            group_format = "YYYY-Q"
        else:  # yearly
            date_from = current_date - timedelta(days=1825)  # Last 5 years
            group_format = "YYYY"
        
        # Volume trends
        volume_trends_query = select(
            extract('year', Procurement.published_date).label('year'),
            extract('month', Procurement.published_date).label('month'),
            func.count(Procurement.id).label('count')
        ).where(
            Procurement.published_date >= date_from
        ).group_by('year', 'month').order_by('year', 'month')
        
        volume_result = await db.execute(volume_trends_query)
        volume_trends = [
            {
                "period": f"{int(row.year)}-{int(row.month):02d}",
                "value": row.count,
                "change_percent": 0.0  # TODO: Calculate change
            }
            for row in volume_result.fetchall()
        ]
        
        # Value trends
        value_trends_query = select(
            extract('year', Procurement.published_date).label('year'),
            extract('month', Procurement.published_date).label('month'),
            func.sum(Procurement.estimated_amount).label('total_value')
        ).where(
            Procurement.published_date >= date_from
        ).group_by('year', 'month').order_by('year', 'month')
        
        value_result = await db.execute(value_trends_query)
        value_trends = [
            {
                "period": f"{int(row.year)}-{int(row.month):02d}",
                "value": float(row.total_value or 0),
                "change_percent": 0.0  # TODO: Calculate change
            }
            for row in value_result.fetchall()
        ]
        
        return TrendAnalysis(
            volume_trends=volume_trends,
            value_trends=value_trends,
            competition_trends=[],  # TODO: Calculate
            efficiency_trends=[],  # TODO: Calculate
            seasonal_patterns=[],  # TODO: Calculate
            forecasts=[],  # TODO: Calculate forecasts
            period=period,
            date_from=date_from,
            date_to=current_date,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate trend analysis: {str(e)}"
        )


@router.post("/custom", response_model=CustomAnalyticsResponse)
async def custom_analytics(
    request: CustomAnalyticsRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Generate custom analytics based on user-defined parameters.
    """
    try:
        # For MVP, provide basic custom analytics
        # In production, this would support complex queries and filters
        
        # Apply date filters
        conditions = []
        if request.date_from:
            conditions.append(Procurement.published_date >= request.date_from)
        if request.date_to:
            conditions.append(Procurement.published_date <= request.date_to)
        
        # Apply custom filters
        for filter_item in request.filters:
            field = filter_item.get("field")
            operator = filter_item.get("operator", "eq")
            value = filter_item.get("value")
            
            if field == "customer_biin" and operator == "eq":
                conditions.append(Procurement.customer_biin == value)
            elif field == "estimated_amount" and operator == "gte":
                conditions.append(Procurement.estimated_amount >= value)
            # Add more filter conditions as needed
        
        # Execute custom query based on metrics
        results = {}
        
        for metric in request.metrics:
            if metric == "total_count":
                query = select(func.count(Procurement.id))
                if conditions:
                    query = query.where(and_(*conditions))
                result = await db.execute(query)
                results[metric] = result.scalar()
            
            elif metric == "total_value":
                query = select(func.sum(Procurement.estimated_amount))
                if conditions:
                    query = query.where(and_(*conditions))
                result = await db.execute(query)
                results[metric] = float(result.scalar() or 0)
            
            elif metric == "average_value":
                query = select(func.avg(Procurement.estimated_amount))
                if conditions:
                    query = query.where(and_(*conditions))
                result = await db.execute(query)
                results[metric] = float(result.scalar() or 0)
        
        return CustomAnalyticsResponse(
            query_id=f"custom_{datetime.utcnow().timestamp()}",
            results=results,
            metadata={
                "filters_applied": len(request.filters),
                "date_range": f"{request.date_from} to {request.date_to}",
                "metrics_count": len(request.metrics)
            },
            execution_time_ms=0,  # Would measure actual execution time
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate custom analytics: {str(e)}"
        ) 