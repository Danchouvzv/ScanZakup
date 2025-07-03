"""
Participant model for procurement participants.

Represents suppliers, customers, and other procurement participants.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base


class Participant(Base):
    """
    Participant model for procurement ecosystem participants.
    
    Includes suppliers, customers, and other entities.
    Based on Goszakup API participant endpoint schema.
    """
    
    __tablename__ = "participant"
    
    # Core identification
    bin = Column(String(12), unique=True, nullable=False, index=True, comment="Business Identification Number")
    iin = Column(String(12), nullable=True, index=True, comment="Individual Identification Number")
    
    # Names
    name_ru = Column(String(500), nullable=True, comment="Name in Russian")
    name_kz = Column(String(500), nullable=True, comment="Name in Kazakh")
    name_en = Column(String(500), nullable=True, comment="Name in English")
    
    # Contact information
    email = Column(String(255), nullable=True, comment="Email address")
    phone = Column(String(50), nullable=True, comment="Phone number")
    website = Column(String(255), nullable=True, comment="Website URL")
    
    # Address information
    address_ru = Column(Text, nullable=True, comment="Address in Russian")
    address_kz = Column(Text, nullable=True, comment="Address in Kazakh")
    postal_code = Column(String(10), nullable=True, comment="Postal code")
    
    # Geographic information
    ref_region_id = Column(Integer, nullable=True, index=True, comment="Region ID")
    region_name_ru = Column(String(200), nullable=True, comment="Region name in Russian")
    region_name_kz = Column(String(200), nullable=True, comment="Region name in Kazakh")
    
    # Participant type and classification
    participant_type = Column(String(20), nullable=True, index=True, comment="Type: supplier, customer, organizer")
    is_government = Column(Boolean, default=False, comment="Government organization")
    is_sme = Column(Boolean, default=False, comment="Small and medium enterprise")
    is_individual = Column(Boolean, default=False, comment="Individual entrepreneur")
    
    # Status information
    is_active = Column(Boolean, default=True, comment="Active status")
    is_blacklisted = Column(Boolean, default=False, index=True, comment="Blacklisted status")
    blacklist_reason_ru = Column(Text, nullable=True, comment="Blacklist reason in Russian")
    blacklist_reason_kz = Column(Text, nullable=True, comment="Blacklist reason in Kazakh")
    blacklist_date = Column(DateTime(timezone=True), nullable=True, comment="Blacklist date")
    
    # Registration information
    registration_date = Column(DateTime(timezone=True), nullable=True, comment="Registration date")
    last_activity_date = Column(DateTime(timezone=True), nullable=True, index=True, comment="Last activity date")
    
    # Economic classification
    oked_code = Column(String(20), nullable=True, comment="OKED classification code")
    oked_name_ru = Column(String(500), nullable=True, comment="OKED name in Russian")
    oked_name_kz = Column(String(500), nullable=True, comment="OKED name in Kazakh")
    
    # Financial information
    authorized_capital = Column(String(100), nullable=True, comment="Authorized capital")
    employee_count = Column(Integer, nullable=True, comment="Number of employees")
    
    # Statistics (can be updated by background jobs)
    total_procurements_won = Column(Integer, default=0, comment="Total procurements won")
    total_contracts_signed = Column(Integer, default=0, comment="Total contracts signed")
    total_contract_sum = Column(String(100), nullable=True, comment="Total contract sum (as string due to large numbers)")
    
    # Raw data backup
    raw_data = Column(JSONB, nullable=True, comment="Original JSON from API")
    
    # Sync information
    last_updated_goszakup = Column(DateTime(timezone=True), nullable=True, comment="Last update from Goszakup")
    sync_status = Column(String(20), default="pending", comment="Sync status")
    sync_error = Column(Text, nullable=True, comment="Sync error message")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_participant_bin", "bin"),
        Index("idx_participant_iin", "iin"),
        Index("idx_participant_type", "participant_type"),
        Index("idx_participant_region", "ref_region_id"),
        Index("idx_participant_blacklist", "is_blacklisted"),
        Index("idx_participant_active", "is_active"),
        Index("idx_participant_search_text", "name_ru", postgresql_using="gin", postgresql_ops={"name_ru": "gin_trgm_ops"}),
        Index("idx_participant_last_activity", "last_activity_date"),
    )
    
    def __repr__(self):
        return f"<Participant(bin={self.bin}, name='{self.display_name[:30]}...')>"
    
    @property
    def display_name(self) -> str:
        """Get display name in Russian, Kazakh, or English."""
        return self.name_ru or self.name_kz or self.name_en or f"Participant {self.bin}"
    
    @property
    def identification(self) -> str:
        """Get primary identification number."""
        return self.bin or self.iin or "N/A"
    
    @property
    def full_address(self) -> str:
        """Get full address string."""
        addr = self.address_ru or self.address_kz or ""
        if self.postal_code and addr:
            return f"{addr}, {self.postal_code}"
        return addr or "N/A"
    
    @property
    def region_name(self) -> str:
        """Get region name in Russian or Kazakh."""
        return self.region_name_ru or self.region_name_kz or ""
    
    @property
    def status_display(self) -> str:
        """Get human-readable status."""
        if self.is_blacklisted:
            return "Blacklisted"
        elif not self.is_active:
            return "Inactive"
        else:
            return "Active"
    
    @property
    def type_display(self) -> str:
        """Get human-readable participant type."""
        type_map = {
            "supplier": "Supplier",
            "customer": "Customer", 
            "organizer": "Organizer",
        }
        return type_map.get(self.participant_type, self.participant_type or "Unknown")
    
    @property
    def classification_display(self) -> str:
        """Get classification display string."""
        classifications = []
        if self.is_government:
            classifications.append("Government")
        if self.is_sme:
            classifications.append("SME")
        if self.is_individual:
            classifications.append("Individual")
        
        return ", ".join(classifications) if classifications else "Organization"
    
    @property
    def oked_display(self) -> str:
        """Get OKED classification display."""
        if self.oked_code and self.oked_name_ru:
            return f"{self.oked_code} - {self.oked_name_ru}"
        return self.oked_code or "N/A" 