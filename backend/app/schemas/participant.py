"""
Participant schema models.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import Field, EmailStr

from .base import BaseSchema, BaseFilterParams, TimestampMixin, StatsResponse


class ParticipantBase(BaseSchema):
    """Base participant fields."""
    
    iin_bin: str = Field(description="IIN/BIN identifier")
    name_ru: str = Field(description="Participant name in Russian")
    name_kz: Optional[str] = Field(None, description="Participant name in Kazakh")
    ref_subject_type: int = Field(description="Subject type reference")
    is_single_org: bool = Field(description="Whether it's a single organization")
    system_id: Optional[str] = Field(None, description="System identifier")
    email: Optional[EmailStr] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    address: Optional[str] = Field(None, description="Address")


class ParticipantOut(ParticipantBase, TimestampMixin):
    """Participant list response model."""
    
    id: int = Field(description="Participant ID")
    
    # Computed fields
    subject_type_name_ru: Optional[str] = Field(None, description="Subject type name in Russian")
    subject_type_name_kz: Optional[str] = Field(None, description="Subject type name in Kazakh")
    
    # Activity indicators
    is_active: Optional[bool] = Field(None, description="Whether participant is active")
    is_blacklisted: Optional[bool] = Field(None, description="Whether participant is blacklisted")
    
    # Statistics
    procurements_count: Optional[int] = Field(None, description="Number of procurements participated")
    contracts_count: Optional[int] = Field(None, description="Number of contracts signed")
    total_contract_value: Optional[float] = Field(None, description="Total contract value")
    
    # Performance indicators
    success_rate: Optional[float] = Field(None, description="Success rate percentage")
    last_activity_date: Optional[datetime] = Field(None, description="Last activity date")


class ParticipantDetail(ParticipantOut):
    """Detailed participant response with full information."""
    
    # Additional details
    description_ru: Optional[str] = Field(None, description="Description in Russian")
    description_kz: Optional[str] = Field(None, description="Description in Kazakh")
    
    # Registration details
    registration_date: Optional[datetime] = Field(None, description="Registration date")
    registration_number: Optional[str] = Field(None, description="Registration number")
    legal_form_ru: Optional[str] = Field(None, description="Legal form in Russian")
    legal_form_kz: Optional[str] = Field(None, description="Legal form in Kazakh")
    
    # Location details
    region_ru: Optional[str] = Field(None, description="Region in Russian")
    region_kz: Optional[str] = Field(None, description="Region in Kazakh")
    city_ru: Optional[str] = Field(None, description="City in Russian")
    city_kz: Optional[str] = Field(None, description="City in Kazakh")
    postal_code: Optional[str] = Field(None, description="Postal code")
    
    # Contact information
    website: Optional[str] = Field(None, description="Website URL")
    fax: Optional[str] = Field(None, description="Fax number")
    contact_person_ru: Optional[str] = Field(None, description="Contact person in Russian")
    contact_person_kz: Optional[str] = Field(None, description="Contact person in Kazakh")
    
    # Business information
    activity_types: Optional[List[str]] = Field(None, description="Types of business activity")
    specializations: Optional[List[str]] = Field(None, description="Specializations")
    certifications: Optional[List[str]] = Field(None, description="Certifications")
    
    # Financial information
    authorized_capital: Optional[float] = Field(None, description="Authorized capital")
    annual_revenue: Optional[float] = Field(None, description="Annual revenue")
    employee_count: Optional[int] = Field(None, description="Number of employees")
    
    # Performance metrics
    total_procurements: int = Field(description="Total procurements participated")
    won_procurements: int = Field(description="Number of won procurements")
    success_rate: float = Field(description="Success rate percentage")
    average_contract_value: Optional[float] = Field(None, description="Average contract value")
    
    # Contract statistics
    active_contracts: int = Field(description="Number of active contracts")
    completed_contracts: int = Field(description="Number of completed contracts")
    total_contract_value: float = Field(description="Total value of all contracts")
    
    # Compliance information
    compliance_status: Optional[str] = Field(None, description="Compliance status")
    last_audit_date: Optional[datetime] = Field(None, description="Last audit date")
    rating: Optional[float] = Field(None, description="Participant rating")
    
    # Relationship indicators
    is_preferred_supplier: Optional[bool] = Field(None, description="Whether it's a preferred supplier")
    partnership_level: Optional[str] = Field(None, description="Partnership level")


class ParticipantFilter(BaseFilterParams):
    """Participant filtering and search parameters."""
    
    # Search
    q: Optional[str] = Field(None, description="Search in name, IIN/BIN, or description")
    
    # Basic filters
    iin_bin: Optional[str] = Field(None, description="Filter by exact IIN/BIN")
    subject_type: Optional[List[int]] = Field(None, description="Filter by subject type IDs")
    
    # Activity filters
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_blacklisted: Optional[bool] = Field(None, description="Filter by blacklist status")
    is_single_org: Optional[bool] = Field(None, description="Filter by organization type")
    
    # Location filters
    region: Optional[str] = Field(None, description="Filter by region")
    city: Optional[str] = Field(None, description="Filter by city")
    
    # Performance filters
    success_rate_min: Optional[float] = Field(None, description="Minimum success rate")
    success_rate_max: Optional[float] = Field(None, description="Maximum success rate")
    
    # Contract value filters
    total_value_from: Optional[float] = Field(None, description="Minimum total contract value")
    total_value_to: Optional[float] = Field(None, description="Maximum total contract value")
    
    # Activity date filters
    last_activity_from: Optional[datetime] = Field(None, description="Last activity from date")
    last_activity_to: Optional[datetime] = Field(None, description="Last activity to date")
    registration_from: Optional[datetime] = Field(None, description="Registration from date")
    registration_to: Optional[datetime] = Field(None, description="Registration to date")
    
    # Contract count filters
    min_contracts: Optional[int] = Field(None, description="Minimum number of contracts")
    max_contracts: Optional[int] = Field(None, description="Maximum number of contracts")
    
    # Business filters
    has_certifications: Optional[bool] = Field(None, description="Has certifications")
    employee_count_min: Optional[int] = Field(None, description="Minimum employee count")
    employee_count_max: Optional[int] = Field(None, description="Maximum employee count")
    
    # Sorting options
    sort_by: Optional[str] = Field(
        "name_ru",
        description="Sort field: name_ru, total_contract_value, success_rate, last_activity_date"
    )


class ParticipantStats(StatsResponse):
    """Participant statistics response."""
    
    # Basic counts
    total_participants: int = Field(description="Total number of participants")
    active_participants: int = Field(description="Number of active participants")
    blacklisted_participants: int = Field(description="Number of blacklisted participants")
    single_organizations: int = Field(description="Number of single organizations")
    
    # Performance statistics
    average_success_rate: float = Field(description="Average success rate percentage")
    total_contract_value: float = Field(description="Total value of all contracts")
    average_contract_value: float = Field(description="Average contract value")
    
    # Activity statistics
    participants_this_month: int = Field(description="New participants this month")
    participants_this_year: int = Field(description="New participants this year")
    active_this_month: int = Field(description="Active participants this month")
    
    # Distribution statistics
    by_subject_type: dict = Field(default_factory=dict, description="Distribution by subject type")
    by_region: dict = Field(default_factory=dict, description="Distribution by region")
    by_success_rate: dict = Field(default_factory=dict, description="Distribution by success rate")
    by_contract_count: dict = Field(default_factory=dict, description="Distribution by contract count")
    
    # Top performers
    top_suppliers: List[dict] = Field(default_factory=list, description="Top suppliers by volume")
    top_customers: List[dict] = Field(default_factory=list, description="Top customers by spending")
    most_active: List[dict] = Field(default_factory=list, description="Most active participants")
    
    # Trends
    registration_trends: List[dict] = Field(default_factory=list, description="Registration trends")
    activity_trends: List[dict] = Field(default_factory=list, description="Activity trends")


class ParticipantCreate(ParticipantBase):
    """Create participant request model."""
    pass


class ParticipantUpdate(BaseSchema):
    """Update participant request model."""
    
    name_ru: Optional[str] = None
    name_kz: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None 