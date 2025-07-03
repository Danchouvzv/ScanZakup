"""
TrdBuy model for procurement announcements.

Represents the main procurement announcement entity from Goszakup API.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import Column, String, Integer, DateTime, Text, Numeric, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class TrdBuy(Base):
    """
    Procurement announcement (trd_buy) model.
    
    Based on Goszakup API v2/v3 trd_buy endpoint schema.
    """
    
    __tablename__ = "trd_buy"
    
    # Core identification
    goszakup_id = Column(Integer, unique=True, nullable=False, index=True, comment="ID from Goszakup API")
    number = Column(String(50), nullable=True, index=True, comment="Procurement number")
    
    # Names and descriptions
    name_ru = Column(Text, nullable=True, comment="Name in Russian")
    name_kz = Column(Text, nullable=True, comment="Name in Kazakh")
    description_ru = Column(Text, nullable=True, comment="Description in Russian")
    description_kz = Column(Text, nullable=True, comment="Description in Kazakh")
    
    # Customer information
    customer_bin = Column(String(12), nullable=True, index=True, comment="Customer BIN")
    customer_name_ru = Column(String(500), nullable=True, comment="Customer name in Russian")
    customer_name_kz = Column(String(500), nullable=True, comment="Customer name in Kazakh")
    
    # Organizer information (if different from customer)
    organizer_bin = Column(String(12), nullable=True, index=True, comment="Organizer BIN") 
    organizer_name_ru = Column(String(500), nullable=True, comment="Organizer name in Russian")
    organizer_name_kz = Column(String(500), nullable=True, comment="Organizer name in Kazakh")
    
    # Financial information
    planned_sum = Column(Numeric(15, 2), nullable=True, comment="Planned sum")
    ref_trade_methods_id = Column(Integer, nullable=True, comment="Trade method ID")
    ref_subject_type_id = Column(Integer, nullable=True, comment="Subject type ID")
    
    # Status and workflow
    ref_buy_status_id = Column(Integer, nullable=True, index=True, comment="Buy status ID")
    buy_status_name_ru = Column(String(100), nullable=True, comment="Status name in Russian")
    buy_status_name_kz = Column(String(100), nullable=True, comment="Status name in Kazakh")
    
    # Important dates
    publish_date = Column(DateTime(timezone=True), nullable=True, index=True, comment="Publication date")
    start_date = Column(DateTime(timezone=True), nullable=True, comment="Start date")
    end_date = Column(DateTime(timezone=True), nullable=True, comment="End date")
    itogi_date_public = Column(DateTime(timezone=True), nullable=True, comment="Results publication date")
    
    # Location
    ref_region_id = Column(Integer, nullable=True, comment="Region ID") 
    region_name_ru = Column(String(200), nullable=True, comment="Region name in Russian")
    region_name_kz = Column(String(200), nullable=True, comment="Region name in Kazakh")
    
    # Additional fields
    lots_count = Column(Integer, default=0, comment="Number of lots")
    is_sme = Column(Boolean, default=False, comment="For small and medium enterprises")
    is_construction = Column(Boolean, default=False, comment="Construction procurement")
    
    # Year for partitioning and quick filtering
    year = Column(Integer, nullable=True, index=True, comment="Procurement year")
    
    # Raw data backup
    raw_data = Column(JSONB, nullable=True, comment="Original JSON from API")
    
    # Timestamps for data synchronization
    last_updated_goszakup = Column(DateTime(timezone=True), nullable=True, comment="Last update timestamp from Goszakup")
    sync_status = Column(String(20), default="pending", comment="Sync status: pending, success, error")
    sync_error = Column(Text, nullable=True, comment="Sync error message if any")
    
    # Relationships
    lots = relationship("Lot", back_populates="trd_buy", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_trd_buy_customer_publish", "customer_bin", "publish_date"),
        Index("idx_trd_buy_status_year", "ref_buy_status_id", "year"),
        Index("idx_trd_buy_planned_sum", "planned_sum"),
        Index("idx_trd_buy_search_text", "name_ru", postgresql_using="gin", postgresql_ops={"name_ru": "gin_trgm_ops"}),
        Index("idx_trd_buy_sync", "sync_status", "last_updated_goszakup"),
    )
    
    def __repr__(self):
        return f"<TrdBuy(id={self.goszakup_id}, name='{self.name_ru[:50]}...')>"
    
    @property
    def display_name(self) -> str:
        """Get display name in Russian or Kazakh."""
        return self.name_ru or self.name_kz or f"Procurement #{self.number}"
    
    @property
    def customer_name(self) -> str:
        """Get customer name in Russian or Kazakh."""
        return self.customer_name_ru or self.customer_name_kz or ""
    
    @property
    def is_active(self) -> bool:
        """Check if procurement is currently active."""
        if not self.start_date or not self.end_date:
            return False
        
        now = datetime.utcnow()
        return self.start_date <= now <= self.end_date
    
    @property
    def days_remaining(self) -> Optional[int]:
        """Get number of days remaining until end date."""
        if not self.end_date:
            return None
        
        now = datetime.utcnow()
        if now > self.end_date:
            return 0
        
        return (self.end_date - now).days 