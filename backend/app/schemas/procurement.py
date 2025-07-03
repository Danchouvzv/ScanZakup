"""
Procurement (TrdBuy) schema models.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import Field

from .base import BaseSchema, BaseFilterParams, TimestampMixin, StatsResponse


class ProcurementBase(BaseSchema):
    """Base procurement fields."""
    
    trd_buy_number_anno: str = Field(description="Procurement announcement number")
    name_ru: str = Field(description="Procurement name in Russian")
    name_kz: Optional[str] = Field(None, description="Procurement name in Kazakh")
    ref_buy_status: int = Field(description="Procurement status reference")
    ref_type_trade: int = Field(description="Trade type reference")
    total_sum: Decimal = Field(description="Total procurement sum")
    count_lot: int = Field(description="Number of lots")
    ref_subject_type: int = Field(description="Subject type reference")
    customer_bin: str = Field(description="Customer BIN")
    start_date: datetime = Field(description="Procurement start date")
    end_date: datetime = Field(description="Procurement end date")


class ProcurementOut(ProcurementBase, TimestampMixin):
    """Procurement list response model."""
    
    id: int = Field(description="Procurement ID")
    
    # Computed fields
    status_name_ru: Optional[str] = Field(None, description="Status name in Russian")
    status_name_kz: Optional[str] = Field(None, description="Status name in Kazakh")
    customer_name_ru: Optional[str] = Field(None, description="Customer name in Russian")
    trade_type_name_ru: Optional[str] = Field(None, description="Trade type name in Russian")
    
    # Statistics
    lots_count: Optional[int] = Field(None, description="Actual number of lots")
    contracts_count: Optional[int] = Field(None, description="Number of contracts")
    is_active: Optional[bool] = Field(None, description="Whether procurement is active")


class ProcurementDetail(ProcurementOut):
    """Detailed procurement response with related data."""
    
    # Additional details
    description_ru: Optional[str] = Field(None, description="Detailed description in Russian")
    description_kz: Optional[str] = Field(None, description="Detailed description in Kazakh")
    
    # Dates
    published_date: Optional[datetime] = Field(None, description="Publication date")
    updated_date: Optional[datetime] = Field(None, description="Last update date")
    
    # Additional info
    ref_trade_methods: Optional[int] = Field(None, description="Trade methods reference")
    ref_subject_types: Optional[List[int]] = Field(None, description="Subject types list")
    
    # Customer details
    customer_name_ru: Optional[str] = Field(None, description="Customer full name in Russian")
    customer_name_kz: Optional[str] = Field(None, description="Customer full name in Kazakh")
    customer_address: Optional[str] = Field(None, description="Customer address")
    customer_phone: Optional[str] = Field(None, description="Customer phone")
    customer_email: Optional[str] = Field(None, description="Customer email")
    
    # Statistics and metrics
    total_applications: Optional[int] = Field(None, description="Total applications received")
    unique_suppliers: Optional[int] = Field(None, description="Number of unique suppliers")
    competition_level: Optional[float] = Field(None, description="Competition level ratio")
    
    # Related data counts
    lots_count: int = Field(description="Number of lots")
    contracts_count: int = Field(description="Number of contracts")
    participants_count: int = Field(description="Number of participants")


class ProcurementFilter(BaseFilterParams):
    """Procurement filtering and search parameters."""
    
    # Search
    q: Optional[str] = Field(None, description="Search in name, number, or description")
    
    # Status and type filters
    status: Optional[List[int]] = Field(None, description="Filter by status IDs")
    trade_type: Optional[List[int]] = Field(None, description="Filter by trade type IDs")
    subject_type: Optional[List[int]] = Field(None, description="Filter by subject type IDs")
    
    # Date range filters
    date_from: Optional[datetime] = Field(None, description="Start date filter")
    date_to: Optional[datetime] = Field(None, description="End date filter")
    published_from: Optional[datetime] = Field(None, description="Published date from")
    published_to: Optional[datetime] = Field(None, description="Published date to")
    
    # Customer filters
    customer_bin: Optional[str] = Field(None, description="Filter by customer BIN")
    customer_region: Optional[str] = Field(None, description="Filter by customer region")
    
    # Value filters
    sum_from: Optional[Decimal] = Field(None, description="Minimum total sum")
    sum_to: Optional[Decimal] = Field(None, description="Maximum total sum")
    
    # Activity filters
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    has_lots: Optional[bool] = Field(None, description="Has lots")
    has_contracts: Optional[bool] = Field(None, description="Has contracts")
    
    # Sorting options
    sort_by: Optional[str] = Field(
        "created_at",
        description="Sort field: created_at, total_sum, start_date, end_date, name_ru"
    )


class ProcurementStats(StatsResponse):
    """Procurement statistics response."""
    
    # Basic counts
    total_procurements: int = Field(description="Total number of procurements")
    active_procurements: int = Field(description="Number of active procurements")
    completed_procurements: int = Field(description="Number of completed procurements")
    
    # Value statistics
    total_value: Decimal = Field(description="Total value of all procurements")
    average_value: Decimal = Field(description="Average procurement value")
    median_value: Optional[Decimal] = Field(None, description="Median procurement value")
    
    # Time-based statistics
    procurements_this_month: int = Field(description="Procurements published this month")
    procurements_this_year: int = Field(description="Procurements published this year")
    
    # Distribution statistics
    by_status: dict = Field(default_factory=dict, description="Distribution by status")
    by_trade_type: dict = Field(default_factory=dict, description="Distribution by trade type")
    by_customer_region: dict = Field(default_factory=dict, description="Distribution by region")
    
    # Trends
    monthly_trends: List[dict] = Field(default_factory=list, description="Monthly trends data")
    top_customers: List[dict] = Field(default_factory=list, description="Top customers by volume")


class ProcurementCreate(ProcurementBase):
    """Create procurement request model."""
    pass


class ProcurementUpdate(BaseSchema):
    """Update procurement request model."""
    
    name_ru: Optional[str] = None
    name_kz: Optional[str] = None
    ref_buy_status: Optional[int] = None
    total_sum: Optional[Decimal] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None 