"""
Lot model for procurement items.

Represents individual lots within procurement announcements.
"""

from decimal import Decimal
from typing import Optional
from sqlalchemy import Column, String, Integer, DateTime, Text, Numeric, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class Lot(Base):
    """
    Procurement lot model.
    
    Represents individual items/lots within a procurement announcement.
    Based on Goszakup API lot endpoint schema.
    """
    
    __tablename__ = "lot"
    
    # Core identification
    goszakup_id = Column(Integer, unique=True, nullable=False, index=True, comment="ID from Goszakup API")
    lot_number = Column(Integer, nullable=True, comment="Lot number within procurement")
    
    # Foreign key to parent procurement
    trd_buy_id = Column(Integer, ForeignKey("trd_buy.id", ondelete="CASCADE"), nullable=False, index=True)
    trd_buy_goszakup_id = Column(Integer, nullable=True, index=True, comment="Parent trd_buy Goszakup ID")
    
    # Item descriptions
    name_ru = Column(Text, nullable=True, comment="Lot name in Russian")
    name_kz = Column(Text, nullable=True, comment="Lot name in Kazakh")
    description_ru = Column(Text, nullable=True, comment="Description in Russian")
    description_kz = Column(Text, nullable=True, comment="Description in Kazakh")
    
    # KTRU classification
    ktru_code = Column(String(20), nullable=True, index=True, comment="KTRU classification code")
    ktru_name_ru = Column(String(500), nullable=True, comment="KTRU name in Russian")
    ktru_name_kz = Column(String(500), nullable=True, comment="KTRU name in Kazakh")
    
    # Quantity and units
    count = Column(Numeric(15, 3), nullable=True, comment="Quantity")
    unit_code = Column(String(10), nullable=True, comment="Unit code")
    unit_name_ru = Column(String(100), nullable=True, comment="Unit name in Russian")
    unit_name_kz = Column(String(100), nullable=True, comment="Unit name in Kazakh")
    
    # Financial information
    unit_price = Column(Numeric(15, 2), nullable=True, comment="Unit price")
    total_sum = Column(Numeric(15, 2), nullable=True, comment="Total sum for lot")
    
    # Status
    ref_lot_status_id = Column(Integer, nullable=True, index=True, comment="Lot status ID")
    lot_status_name_ru = Column(String(100), nullable=True, comment="Lot status in Russian")
    lot_status_name_kz = Column(String(100), nullable=True, comment="Lot status in Kazakh")
    
    # Additional information
    is_nskemi = Column(Boolean, default=False, comment="National supplier classification")
    customer_bin = Column(String(12), nullable=True, index=True, comment="Customer BIN (denormalized)")
    
    # Delivery information
    delivery_place_ru = Column(Text, nullable=True, comment="Delivery place in Russian")
    delivery_place_kz = Column(Text, nullable=True, comment="Delivery place in Kazakh")
    delivery_term = Column(String(200), nullable=True, comment="Delivery terms")
    
    # Raw data backup
    raw_data = Column(JSONB, nullable=True, comment="Original JSON from API")
    
    # Sync information
    last_updated_goszakup = Column(DateTime(timezone=True), nullable=True, comment="Last update from Goszakup")
    sync_status = Column(String(20), default="pending", comment="Sync status")
    sync_error = Column(Text, nullable=True, comment="Sync error message")
    
    # Relationships
    trd_buy = relationship("TrdBuy", back_populates="lots")
    contracts = relationship("Contract", back_populates="lot", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_lot_trd_buy_id", "trd_buy_id"),
        Index("idx_lot_ktru_code", "ktru_code"),
        Index("idx_lot_customer_bin", "customer_bin"),
        Index("idx_lot_status", "ref_lot_status_id"),
        Index("idx_lot_total_sum", "total_sum"),
        Index("idx_lot_search_text", "name_ru", postgresql_using="gin", postgresql_ops={"name_ru": "gin_trgm_ops"}),
    )
    
    def __repr__(self):
        return f"<Lot(id={self.goszakup_id}, name='{self.name_ru[:30]}...')>"
    
    @property
    def display_name(self) -> str:
        """Get display name in Russian or Kazakh."""
        return self.name_ru or self.name_kz or f"Lot #{self.lot_number}"
    
    @property
    def ktru_display(self) -> str:
        """Get KTRU display string."""
        if self.ktru_code and self.ktru_name_ru:
            return f"{self.ktru_code} - {self.ktru_name_ru}"
        return self.ktru_code or "N/A"
    
    @property
    def unit_display(self) -> str:
        """Get unit display string."""
        return self.unit_name_ru or self.unit_name_kz or self.unit_code or "шт"
    
    @property
    def quantity_display(self) -> str:
        """Get formatted quantity with units."""
        if self.count:
            return f"{self.count} {self.unit_display}"
        return "N/A"
    
    @property
    def price_per_unit_display(self) -> str:
        """Get formatted price per unit."""
        if self.unit_price:
            return f"{self.unit_price:,.2f} ₸"
        return "N/A"
    
    @property
    def total_sum_display(self) -> str:
        """Get formatted total sum."""
        if self.total_sum:
            return f"{self.total_sum:,.2f} ₸"
        return "N/A" 