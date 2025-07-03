"""
Lot schema models.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import Field

from .base import BaseSchema, BaseFilterParams, TimestampMixin


class LotBase(BaseSchema):
    """Base lot fields."""
    
    lot_number: int = Field(description="Lot number within procurement")
    ref_lot_status: int = Field(description="Lot status reference")
    subject_biin: str = Field(description="Subject BIIN")
    name_ru: str = Field(description="Lot name in Russian")
    name_kz: Optional[str] = Field(None, description="Lot name in Kazakh")
    quantity: Decimal = Field(description="Lot quantity")
    price: Decimal = Field(description="Lot price per unit")
    sum: Decimal = Field(description="Total lot sum")
    customer_bin: str = Field(description="Customer BIN")
    trd_buy_id: int = Field(description="Related procurement ID")


class LotOut(LotBase, TimestampMixin):
    """Lot list response model."""
    
    id: int = Field(description="Lot ID")
    
    # Computed fields
    status_name_ru: Optional[str] = Field(None, description="Status name in Russian")
    status_name_kz: Optional[str] = Field(None, description="Status name in Kazakh")
    
    # Related procurement info
    procurement_number: Optional[str] = Field(None, description="Procurement announcement number")
    procurement_name_ru: Optional[str] = Field(None, description="Procurement name in Russian")
    
    # Statistics
    applications_count: Optional[int] = Field(None, description="Number of applications")
    contracts_count: Optional[int] = Field(None, description="Number of contracts")
    is_active: Optional[bool] = Field(None, description="Whether lot is active")


class LotDetail(LotOut):
    """Detailed lot response with related data."""
    
    # Additional details
    description_ru: Optional[str] = Field(None, description="Detailed description in Russian")
    description_kz: Optional[str] = Field(None, description="Detailed description in Kazakh")
    
    # Technical specifications
    tech_spec_ru: Optional[str] = Field(None, description="Technical specifications in Russian")
    tech_spec_kz: Optional[str] = Field(None, description="Technical specifications in Kazakh")
    
    # Delivery and terms
    delivery_place_ru: Optional[str] = Field(None, description="Delivery place in Russian")
    delivery_place_kz: Optional[str] = Field(None, description="Delivery place in Kazakh")
    delivery_term_ru: Optional[str] = Field(None, description="Delivery terms in Russian")
    delivery_term_kz: Optional[str] = Field(None, description="Delivery terms in Kazakh")
    
    # Additional info
    ref_units: Optional[int] = Field(None, description="Units reference")
    unit_name_ru: Optional[str] = Field(None, description="Unit name in Russian")
    unit_name_kz: Optional[str] = Field(None, description="Unit name in Kazakh")
    
    # Customer details
    customer_name_ru: Optional[str] = Field(None, description="Customer name in Russian")
    customer_name_kz: Optional[str] = Field(None, description="Customer name in Kazakh")
    
    # Procurement details
    procurement_name_ru: str = Field(description="Related procurement name in Russian")
    procurement_start_date: datetime = Field(description="Procurement start date")
    procurement_end_date: datetime = Field(description="Procurement end date")
    
    # Competition metrics
    applications_count: int = Field(description="Number of applications")
    unique_suppliers: Optional[int] = Field(None, description="Number of unique suppliers")
    competition_level: Optional[float] = Field(None, description="Competition level ratio")
    
    # Contract information
    contracts_count: int = Field(description="Number of contracts")
    total_contracted_sum: Optional[Decimal] = Field(None, description="Total contracted sum")
    savings_amount: Optional[Decimal] = Field(None, description="Savings amount")
    savings_percentage: Optional[float] = Field(None, description="Savings percentage")


class LotFilter(BaseFilterParams):
    """Lot filtering and search parameters."""
    
    # Search
    q: Optional[str] = Field(None, description="Search in lot name or description")
    
    # Basic filters
    status: Optional[List[int]] = Field(None, description="Filter by status IDs")
    lot_number: Optional[int] = Field(None, description="Filter by lot number")
    
    # Related procurement filters
    trd_buy_id: Optional[int] = Field(None, description="Filter by procurement ID")
    procurement_number: Optional[str] = Field(None, description="Filter by procurement number")
    
    # Customer filters
    customer_bin: Optional[str] = Field(None, description="Filter by customer BIN")
    subject_biin: Optional[str] = Field(None, description="Filter by subject BIIN")
    
    # Value filters
    price_from: Optional[Decimal] = Field(None, description="Minimum price")
    price_to: Optional[Decimal] = Field(None, description="Maximum price")
    sum_from: Optional[Decimal] = Field(None, description="Minimum total sum")
    sum_to: Optional[Decimal] = Field(None, description="Maximum total sum")
    quantity_from: Optional[Decimal] = Field(None, description="Minimum quantity")
    quantity_to: Optional[Decimal] = Field(None, description="Maximum quantity")
    
    # Date filters
    date_from: Optional[datetime] = Field(None, description="Created from date")
    date_to: Optional[datetime] = Field(None, description="Created to date")
    
    # Activity filters
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    has_applications: Optional[bool] = Field(None, description="Has applications")
    has_contracts: Optional[bool] = Field(None, description="Has contracts")
    
    # Sorting options
    sort_by: Optional[str] = Field(
        "created_at",
        description="Sort field: created_at, sum, price, quantity, lot_number"
    )


class LotCreate(LotBase):
    """Create lot request model."""
    pass


class LotUpdate(BaseSchema):
    """Update lot request model."""
    
    name_ru: Optional[str] = None
    name_kz: Optional[str] = None
    ref_lot_status: Optional[int] = None
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    sum: Optional[Decimal] = None 