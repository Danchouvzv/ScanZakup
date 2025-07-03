"""
Contract model for signed procurement contracts.

Represents contracts signed between customers and suppliers.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Column, String, Integer, DateTime, Text, Numeric, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class Contract(Base):
    """
    Contract model for signed procurement agreements.
    
    Based on Goszakup API contract endpoint schema.
    """
    
    __tablename__ = "contract"
    
    # Core identification
    goszakup_id = Column(Integer, unique=True, nullable=False, index=True, comment="ID from Goszakup API")
    contract_number = Column(String(100), nullable=True, index=True, comment="Contract number")
    
    # Foreign keys
    lot_id = Column(Integer, ForeignKey("lot.id", ondelete="CASCADE"), nullable=True, index=True)
    lot_goszakup_id = Column(Integer, nullable=True, index=True, comment="Lot Goszakup ID")
    trd_buy_goszakup_id = Column(Integer, nullable=True, index=True, comment="Parent trd_buy Goszakup ID")
    
    # Contract details
    description_ru = Column(Text, nullable=True, comment="Contract description in Russian")
    description_kz = Column(Text, nullable=True, comment="Contract description in Kazakh")
    
    # Financial information
    sum = Column(Numeric(15, 2), nullable=True, comment="Contract sum")
    supplier_sum = Column(Numeric(15, 2), nullable=True, comment="Supplier sum")
    
    # Customer information (denormalized for reporting)
    customer_bin = Column(String(12), nullable=True, index=True, comment="Customer BIN")
    customer_name_ru = Column(String(500), nullable=True, comment="Customer name in Russian")
    customer_name_kz = Column(String(500), nullable=True, comment="Customer name in Kazakh")
    
    # Supplier information
    supplier_bin = Column(String(12), nullable=True, index=True, comment="Supplier BIN")
    supplier_name_ru = Column(String(500), nullable=True, comment="Supplier name in Russian")
    supplier_name_kz = Column(String(500), nullable=True, comment="Supplier name in Kazakh")
    supplier_iin = Column(String(12), nullable=True, comment="Supplier IIN if individual")
    
    # Contract status
    ref_contract_status_id = Column(Integer, nullable=True, index=True, comment="Contract status ID")
    contract_status_name_ru = Column(String(100), nullable=True, comment="Contract status in Russian")
    contract_status_name_kz = Column(String(100), nullable=True, comment="Contract status in Kazakh")
    
    # Important dates
    date_sign = Column(DateTime(timezone=True), nullable=True, index=True, comment="Contract signing date")
    date_create = Column(DateTime(timezone=True), nullable=True, comment="Contract creation date")
    execution_start_date = Column(DateTime(timezone=True), nullable=True, comment="Execution start date")
    execution_end_date = Column(DateTime(timezone=True), nullable=True, comment="Execution end date")
    
    # Contract execution
    is_executed = Column(Boolean, default=False, comment="Contract execution status")
    execution_percent = Column(Numeric(5, 2), nullable=True, comment="Execution percentage")
    
    # Payment information
    paid_sum = Column(Numeric(15, 2), nullable=True, comment="Paid amount")
    debt_sum = Column(Numeric(15, 2), nullable=True, comment="Debt amount")
    
    # Additional information
    ref_trade_methods_id = Column(Integer, nullable=True, comment="Trade method ID")
    ref_subject_type_id = Column(Integer, nullable=True, comment="Subject type ID")
    
    # Location
    ref_region_id = Column(Integer, nullable=True, comment="Region ID")
    region_name_ru = Column(String(200), nullable=True, comment="Region name in Russian")
    region_name_kz = Column(String(200), nullable=True, comment="Region name in Kazakh")
    
    # Year for partitioning
    year = Column(Integer, nullable=True, index=True, comment="Contract year")
    
    # Raw data backup
    raw_data = Column(JSONB, nullable=True, comment="Original JSON from API")
    
    # Sync information
    last_updated_goszakup = Column(DateTime(timezone=True), nullable=True, comment="Last update from Goszakup")
    sync_status = Column(String(20), default="pending", comment="Sync status")
    sync_error = Column(Text, nullable=True, comment="Sync error message")
    
    # Relationships
    lot = relationship("Lot", back_populates="contracts")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_contract_lot_id", "lot_id"),
        Index("idx_contract_customer_bin", "customer_bin"),
        Index("idx_contract_supplier_bin", "supplier_bin"),
        Index("idx_contract_date_sign", "date_sign"),
        Index("idx_contract_status", "ref_contract_status_id"),
        Index("idx_contract_sum", "sum"),
        Index("idx_contract_year", "year"),
        Index("idx_contract_customer_year", "customer_bin", "year"),
        Index("idx_contract_supplier_year", "supplier_bin", "year"),
    )
    
    def __repr__(self):
        return f"<Contract(id={self.goszakup_id}, number='{self.contract_number}')>"
    
    @property
    def display_name(self) -> str:
        """Get display name for contract."""
        if self.contract_number:
            return f"Contract #{self.contract_number}"
        return f"Contract {self.goszakup_id}"
    
    @property
    def customer_name(self) -> str:
        """Get customer name in Russian or Kazakh."""
        return self.customer_name_ru or self.customer_name_kz or ""
    
    @property
    def supplier_name(self) -> str:
        """Get supplier name in Russian or Kazakh."""
        return self.supplier_name_ru or self.supplier_name_kz or ""
    
    @property
    def sum_display(self) -> str:
        """Get formatted contract sum."""
        if self.sum:
            return f"{self.sum:,.2f} ₸"
        return "N/A"
    
    @property
    def is_active(self) -> bool:
        """Check if contract is currently active."""
        if not self.execution_start_date or not self.execution_end_date:
            return False
        
        now = datetime.utcnow()
        return self.execution_start_date <= now <= self.execution_end_date
    
    @property
    def days_until_completion(self) -> Optional[int]:
        """Get days until contract completion."""
        if not self.execution_end_date:
            return None
        
        now = datetime.utcnow()
        if now > self.execution_end_date:
            return 0
        
        return (self.execution_end_date - now).days
    
    @property
    def execution_status(self) -> str:
        """Get human-readable execution status."""
        if self.is_executed:
            return "Executed"
        elif self.execution_percent:
            return f"{self.execution_percent}% Complete"
        elif self.is_active:
            return "In Progress"
        else:
            return "Pending" 