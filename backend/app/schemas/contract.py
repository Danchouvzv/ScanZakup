"""
Contract schema models.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import Field

from .base import BaseSchema, BaseFilterParams, TimestampMixin, StatsResponse


class ContractBase(BaseSchema):
    """Base contract fields."""
    
    contract_number: str = Field(description="Contract number")
    ref_contract_status: int = Field(description="Contract status reference")
    supplier_biin: str = Field(description="Supplier BIIN")
    customer_bin: str = Field(description="Customer BIN")
    subject_biin: str = Field(description="Subject BIIN")
    contract_sum: Decimal = Field(description="Contract sum")
    sign_date: datetime = Field(description="Contract signing date")
    ec_end_date: datetime = Field(description="Expected completion date")
    lot_id: int = Field(description="Related lot ID")
    trd_buy_id: int = Field(description="Related procurement ID")


class ContractOut(ContractBase, TimestampMixin):
    """Contract list response model."""
    
    id: int = Field(description="Contract ID")
    
    # Computed fields
    status_name_ru: Optional[str] = Field(None, description="Status name in Russian")
    status_name_kz: Optional[str] = Field(None, description="Status name in Kazakh")
    
    # Related data
    supplier_name_ru: Optional[str] = Field(None, description="Supplier name in Russian")
    customer_name_ru: Optional[str] = Field(None, description="Customer name in Russian")
    lot_name_ru: Optional[str] = Field(None, description="Lot name in Russian")
    procurement_number: Optional[str] = Field(None, description="Procurement number")
    
    # Performance metrics
    is_active: Optional[bool] = Field(None, description="Whether contract is active")
    is_completed: Optional[bool] = Field(None, description="Whether contract is completed")
    days_to_completion: Optional[int] = Field(None, description="Days until completion")


class ContractDetail(ContractOut):
    """Detailed contract response with related data."""
    
    # Additional contract details
    description_ru: Optional[str] = Field(None, description="Contract description in Russian")
    description_kz: Optional[str] = Field(None, description="Contract description in Kazakh")
    
    # Contract terms
    payment_terms_ru: Optional[str] = Field(None, description="Payment terms in Russian")
    payment_terms_kz: Optional[str] = Field(None, description="Payment terms in Kazakh")
    delivery_terms_ru: Optional[str] = Field(None, description="Delivery terms in Russian")
    delivery_terms_kz: Optional[str] = Field(None, description="Delivery terms in Kazakh")
    
    # Dates and timeline
    actual_end_date: Optional[datetime] = Field(None, description="Actual completion date")
    last_updated_date: Optional[datetime] = Field(None, description="Last update date")
    
    # Financial details
    advance_sum: Optional[Decimal] = Field(None, description="Advance payment sum")
    paid_sum: Optional[Decimal] = Field(None, description="Amount already paid")
    remaining_sum: Optional[Decimal] = Field(None, description="Remaining amount to pay")
    
    # Supplier details
    supplier_name_ru: str = Field(description="Supplier name in Russian")
    supplier_name_kz: Optional[str] = Field(None, description="Supplier name in Kazakh")
    supplier_address: Optional[str] = Field(None, description="Supplier address")
    supplier_phone: Optional[str] = Field(None, description="Supplier phone")
    supplier_email: Optional[str] = Field(None, description="Supplier email")
    
    # Customer details
    customer_name_ru: str = Field(description="Customer name in Russian")
    customer_name_kz: Optional[str] = Field(None, description="Customer name in Kazakh")
    customer_address: Optional[str] = Field(None, description="Customer address")
    
    # Related lot details
    lot_name_ru: str = Field(description="Related lot name in Russian")
    lot_quantity: Decimal = Field(description="Lot quantity")
    lot_sum: Decimal = Field(description="Original lot sum")
    
    # Related procurement details
    procurement_name_ru: str = Field(description="Related procurement name in Russian")
    procurement_number: str = Field(description="Procurement announcement number")
    
    # Performance metrics
    completion_percentage: Optional[float] = Field(None, description="Completion percentage")
    savings_amount: Optional[Decimal] = Field(None, description="Savings compared to lot sum")
    savings_percentage: Optional[float] = Field(None, description="Savings percentage")
    performance_score: Optional[float] = Field(None, description="Performance score")


class ContractFilter(BaseFilterParams):
    """Contract filtering and search parameters."""
    
    # Search
    q: Optional[str] = Field(None, description="Search in contract number, supplier, or customer")
    
    # Basic filters
    status: Optional[List[int]] = Field(None, description="Filter by status IDs")
    contract_number: Optional[str] = Field(None, description="Filter by contract number")
    
    # Related entity filters
    lot_id: Optional[int] = Field(None, description="Filter by lot ID")
    trd_buy_id: Optional[int] = Field(None, description="Filter by procurement ID")
    procurement_number: Optional[str] = Field(None, description="Filter by procurement number")
    
    # Participant filters
    supplier_biin: Optional[str] = Field(None, description="Filter by supplier BIIN")
    customer_bin: Optional[str] = Field(None, description="Filter by customer BIN")
    subject_biin: Optional[str] = Field(None, description="Filter by subject BIIN")
    
    # Value filters
    sum_from: Optional[Decimal] = Field(None, description="Minimum contract sum")
    sum_to: Optional[Decimal] = Field(None, description="Maximum contract sum")
    
    # Date filters
    sign_date_from: Optional[datetime] = Field(None, description="Signed from date")
    sign_date_to: Optional[datetime] = Field(None, description="Signed to date")
    completion_date_from: Optional[datetime] = Field(None, description="Completion from date")
    completion_date_to: Optional[datetime] = Field(None, description="Completion to date")
    
    # Status filters
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_completed: Optional[bool] = Field(None, description="Filter by completion status")
    is_overdue: Optional[bool] = Field(None, description="Filter by overdue status")
    
    # Sorting options
    sort_by: Optional[str] = Field(
        "sign_date",
        description="Sort field: sign_date, contract_sum, ec_end_date, created_at"
    )


class ContractStats(StatsResponse):
    """Contract statistics response."""
    
    # Basic counts
    total_contracts: int = Field(description="Total number of contracts")
    active_contracts: int = Field(description="Number of active contracts")
    completed_contracts: int = Field(description="Number of completed contracts")
    overdue_contracts: int = Field(description="Number of overdue contracts")
    
    # Value statistics
    total_value: Decimal = Field(description="Total value of all contracts")
    average_value: Decimal = Field(description="Average contract value")
    median_value: Optional[Decimal] = Field(None, description="Median contract value")
    
    # Performance statistics
    completion_rate: float = Field(description="Contract completion rate percentage")
    average_completion_time: Optional[float] = Field(None, description="Average completion time in days")
    on_time_completion_rate: float = Field(description="On-time completion rate percentage")
    
    # Financial statistics
    total_savings: Decimal = Field(description="Total savings amount")
    average_savings_percentage: float = Field(description="Average savings percentage")
    total_paid: Decimal = Field(description="Total amount paid")
    
    # Time-based statistics
    contracts_this_month: int = Field(description="Contracts signed this month")
    contracts_this_year: int = Field(description="Contracts signed this year")
    
    # Distribution statistics
    by_status: dict = Field(default_factory=dict, description="Distribution by status")
    by_supplier: dict = Field(default_factory=dict, description="Distribution by supplier")
    by_customer: dict = Field(default_factory=dict, description="Distribution by customer")
    
    # Trends
    monthly_trends: List[dict] = Field(default_factory=list, description="Monthly trends data")
    top_suppliers: List[dict] = Field(default_factory=list, description="Top suppliers by volume")
    top_customers: List[dict] = Field(default_factory=list, description="Top customers by volume")


class ContractCreate(ContractBase):
    """Create contract request model."""
    pass


class ContractUpdate(BaseSchema):
    """Update contract request model."""
    
    ref_contract_status: Optional[int] = None
    contract_sum: Optional[Decimal] = None
    ec_end_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None 