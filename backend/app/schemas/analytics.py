"""
Analytics schema models.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import Field

from .base import BaseSchema, BaseFilterParams


class AnalyticsFilter(BaseFilterParams):
    """Analytics filtering parameters."""
    
    # Date range
    date_from: Optional[datetime] = Field(None, description="Analysis period start date")
    date_to: Optional[datetime] = Field(None, description="Analysis period end date")
    
    # Entity filters
    customer_bin: Optional[str] = Field(None, description="Filter by customer BIN")
    supplier_biin: Optional[str] = Field(None, description="Filter by supplier BIIN")
    region: Optional[str] = Field(None, description="Filter by region")
    
    # Category filters
    trade_type: Optional[List[int]] = Field(None, description="Filter by trade type IDs")
    subject_type: Optional[List[int]] = Field(None, description="Filter by subject type IDs")
    status: Optional[List[int]] = Field(None, description="Filter by status IDs")
    
    # Value filters
    value_from: Optional[Decimal] = Field(None, description="Minimum value filter")
    value_to: Optional[Decimal] = Field(None, description="Maximum value filter")
    
    # Aggregation options
    group_by: Optional[str] = Field(
        "month",
        description="Group by: day, week, month, quarter, year"
    )
    metrics: Optional[List[str]] = Field(
        None,
        description="Specific metrics to include"
    )


class MetricValue(BaseSchema):
    """Individual metric value with metadata."""
    
    value: float = Field(description="Metric value")
    label: str = Field(description="Metric label")
    change: Optional[float] = Field(None, description="Change from previous period")
    change_percentage: Optional[float] = Field(None, description="Percentage change")
    trend: Optional[str] = Field(None, description="Trend direction: up, down, stable")
    format_type: Optional[str] = Field(None, description="Display format: currency, percentage, number")


class TrendPoint(BaseSchema):
    """Single point in a trend series."""
    
    period: str = Field(description="Period label")
    date: datetime = Field(description="Period date")
    value: float = Field(description="Value for this period")
    count: Optional[int] = Field(None, description="Count for this period")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DashboardSummary(BaseSchema):
    """Dashboard summary with key metrics."""
    
    # Overview metrics
    total_procurements: MetricValue = Field(description="Total procurement count")
    total_value: MetricValue = Field(description="Total procurement value")
    active_procurements: MetricValue = Field(description="Active procurement count")
    completed_procurements: MetricValue = Field(description="Completed procurement count")
    
    # Contract metrics
    total_contracts: MetricValue = Field(description="Total contract count")
    contract_value: MetricValue = Field(description="Total contract value")
    average_contract_value: MetricValue = Field(description="Average contract value")
    contract_completion_rate: MetricValue = Field(description="Contract completion rate")
    
    # Participant metrics
    total_suppliers: MetricValue = Field(description="Total supplier count")
    active_suppliers: MetricValue = Field(description="Active supplier count")
    new_suppliers: MetricValue = Field(description="New suppliers this period")
    supplier_diversity: MetricValue = Field(description="Supplier diversity index")
    
    # Performance metrics
    average_competition: MetricValue = Field(description="Average competition level")
    savings_rate: MetricValue = Field(description="Average savings rate")
    time_to_contract: MetricValue = Field(description="Average time to contract")
    compliance_rate: MetricValue = Field(description="Compliance rate")
    
    # Period information
    period_start: datetime = Field(description="Analysis period start")
    period_end: datetime = Field(description="Analysis period end")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class MarketTrends(BaseSchema):
    """Market trends analysis."""
    
    # Volume trends
    procurement_volume_trend: List[TrendPoint] = Field(description="Procurement volume over time")
    contract_volume_trend: List[TrendPoint] = Field(description="Contract volume over time")
    value_trend: List[TrendPoint] = Field(description="Total value over time")
    
    # Competition trends
    competition_trend: List[TrendPoint] = Field(description="Competition level over time")
    new_suppliers_trend: List[TrendPoint] = Field(description="New suppliers over time")
    market_concentration: List[TrendPoint] = Field(description="Market concentration over time")
    
    # Performance trends
    savings_trend: List[TrendPoint] = Field(description="Savings rate over time")
    completion_rate_trend: List[TrendPoint] = Field(description="Completion rate over time")
    time_to_award_trend: List[TrendPoint] = Field(description="Time to award over time")
    
    # Sector analysis
    top_sectors: List[Dict[str, Any]] = Field(description="Top sectors by volume")
    growing_sectors: List[Dict[str, Any]] = Field(description="Fastest growing sectors")
    declining_sectors: List[Dict[str, Any]] = Field(description="Declining sectors")
    
    # Geographic analysis
    regional_distribution: Dict[str, Any] = Field(description="Distribution by region")
    regional_growth: List[Dict[str, Any]] = Field(description="Regional growth rates")
    
    # Analysis metadata
    analysis_period: str = Field(description="Analysis period description")
    data_quality_score: float = Field(description="Data quality score")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class SupplierPerformance(BaseSchema):
    """Supplier performance analysis."""
    
    # Top performers
    top_suppliers_by_volume: List[Dict[str, Any]] = Field(description="Top suppliers by contract volume")
    top_suppliers_by_value: List[Dict[str, Any]] = Field(description="Top suppliers by contract value")
    most_consistent_suppliers: List[Dict[str, Any]] = Field(description="Most consistent performers")
    
    # Performance metrics
    average_success_rate: float = Field(description="Average supplier success rate")
    average_completion_rate: float = Field(description="Average completion rate")
    average_compliance_score: float = Field(description="Average compliance score")
    
    # Competition analysis
    market_concentration_index: float = Field(description="Market concentration index")
    competition_intensity: float = Field(description="Competition intensity score")
    barrier_to_entry_score: float = Field(description="Barrier to entry score")
    
    # Sector performance
    sector_performance: List[Dict[str, Any]] = Field(description="Performance by sector")
    regional_performance: List[Dict[str, Any]] = Field(description="Performance by region")
    
    # Trends
    performance_trends: List[TrendPoint] = Field(description="Performance trends over time")
    market_share_trends: List[TrendPoint] = Field(description="Market share trends")
    
    # Risk analysis
    high_risk_suppliers: List[Dict[str, Any]] = Field(description="High risk suppliers")
    compliance_issues: List[Dict[str, Any]] = Field(description="Compliance issues")
    
    # Analysis metadata
    suppliers_analyzed: int = Field(description="Number of suppliers analyzed")
    analysis_period: str = Field(description="Analysis period")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class CustomerAnalysis(BaseSchema):
    """Customer spending and behavior analysis."""
    
    # Top customers
    top_customers_by_volume: List[Dict[str, Any]] = Field(description="Top customers by procurement volume")
    top_customers_by_value: List[Dict[str, Any]] = Field(description="Top customers by spending")
    most_active_customers: List[Dict[str, Any]] = Field(description="Most active customers")
    
    # Spending patterns
    spending_trends: List[TrendPoint] = Field(description="Customer spending trends")
    seasonal_patterns: List[Dict[str, Any]] = Field(description="Seasonal spending patterns")
    category_preferences: List[Dict[str, Any]] = Field(description="Category preferences")
    
    # Efficiency metrics
    average_procurement_size: float = Field(description="Average procurement size")
    average_time_to_award: float = Field(description="Average time to award")
    repeat_supplier_rate: float = Field(description="Rate of using repeat suppliers")
    
    # Regional analysis
    regional_spending: Dict[str, Any] = Field(description="Spending by region")
    regional_efficiency: List[Dict[str, Any]] = Field(description="Efficiency by region")
    
    # Analysis metadata
    customers_analyzed: int = Field(description="Number of customers analyzed")
    total_spending: Decimal = Field(description="Total spending analyzed")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class CompetitionAnalysis(BaseSchema):
    """Market competition analysis."""
    
    # Competition metrics
    average_bidders_per_lot: float = Field(description="Average number of bidders per lot")
    competition_index: float = Field(description="Competition intensity index")
    market_concentration: float = Field(description="Market concentration ratio")
    
    # Bidding patterns
    bidding_trends: List[TrendPoint] = Field(description="Bidding activity trends")
    win_rate_distribution: List[Dict[str, Any]] = Field(description="Win rate distribution")
    bid_spread_analysis: List[Dict[str, Any]] = Field(description="Bid spread analysis")
    
    # Market segments
    highly_competitive_segments: List[Dict[str, Any]] = Field(description="Highly competitive segments")
    low_competition_segments: List[Dict[str, Any]] = Field(description="Low competition segments")
    emerging_segments: List[Dict[str, Any]] = Field(description="Emerging market segments")
    
    # Supplier behavior
    new_entrants: List[Dict[str, Any]] = Field(description="New market entrants")
    market_exits: List[Dict[str, Any]] = Field(description="Suppliers exiting market")
    market_share_changes: List[Dict[str, Any]] = Field(description="Market share changes")
    
    # Analysis metadata
    lots_analyzed: int = Field(description="Number of lots analyzed")
    time_period: str = Field(description="Analysis time period")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class SavingsAnalysis(BaseSchema):
    """Procurement savings and efficiency analysis."""
    
    # Savings metrics
    total_savings: Decimal = Field(description="Total savings achieved")
    average_savings_rate: float = Field(description="Average savings rate percentage")
    median_savings_rate: float = Field(description="Median savings rate percentage")
    
    # Savings trends
    savings_trends: List[TrendPoint] = Field(description="Savings trends over time")
    savings_by_category: List[Dict[str, Any]] = Field(description="Savings by procurement category")
    savings_by_customer: List[Dict[str, Any]] = Field(description="Savings by customer")
    
    # Efficiency metrics
    cost_reduction_rate: float = Field(description="Cost reduction rate")
    process_efficiency_score: float = Field(description="Process efficiency score")
    value_for_money_index: float = Field(description="Value for money index")
    
    # Best practices
    high_savings_procurements: List[Dict[str, Any]] = Field(description="Procurements with high savings")
    efficiency_leaders: List[Dict[str, Any]] = Field(description="Most efficient customers")
    
    # Analysis metadata
    baseline_value: Decimal = Field(description="Baseline value for comparison")
    analysis_methodology: str = Field(description="Analysis methodology used")
    generated_at: datetime = Field(default_factory=datetime.utcnow) 