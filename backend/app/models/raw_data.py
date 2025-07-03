"""
RawData model for storing unprocessed API responses.

Stores raw JSON responses from Goszakup API for backup and troubleshooting.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Integer, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base


class RawData(Base):
    """
    Raw data storage for API responses.
    
    Stores unprocessed JSON responses from Goszakup API endpoints
    for backup, debugging, and schema evolution protection.
    """
    
    __tablename__ = "raw_data"
    
    # Identification
    endpoint = Column(String(50), nullable=False, index=True, comment="API endpoint name (trd_buy, lot, contract, etc.)")
    entity_id = Column(Integer, nullable=True, index=True, comment="Entity ID from API response")
    request_id = Column(String(100), nullable=True, index=True, comment="Request ID for correlation")
    
    # Request information
    method = Column(String(10), default="GET", comment="HTTP method")
    url = Column(Text, nullable=True, comment="Full request URL")
    query_params = Column(JSONB, nullable=True, comment="Query parameters used")
    
    # Response data
    response_body = Column(JSONB, nullable=False, comment="Raw JSON response body")
    status_code = Column(Integer, nullable=True, comment="HTTP status code")
    response_headers = Column(JSONB, nullable=True, comment="Response headers")
    
    # Timing information
    request_timestamp = Column(DateTime(timezone=True), nullable=False, index=True, comment="When request was made")
    response_time_ms = Column(Integer, nullable=True, comment="Response time in milliseconds")
    
    # Processing status
    processed = Column(String(20), default="pending", index=True, comment="Processing status: pending, success, error, skipped")
    processed_at = Column(DateTime(timezone=True), nullable=True, comment="When processing completed")
    processing_error = Column(Text, nullable=True, comment="Processing error message")
    
    # Data classification
    data_type = Column(String(20), nullable=True, index=True, comment="Data type: announcement, lot, contract, participant")
    year = Column(Integer, nullable=True, index=True, comment="Data year for partitioning")
    
    # Metadata
    api_version = Column(String(10), default="v2", comment="API version used")
    is_delta = Column(String(10), default=False, comment="Whether this is delta sync data")
    
    # Deduplication
    content_hash = Column(String(64), nullable=True, index=True, comment="SHA256 hash of response body for deduplication")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_raw_data_endpoint_timestamp", "endpoint", "request_timestamp"),
        Index("idx_raw_data_entity_endpoint", "entity_id", "endpoint"),
        Index("idx_raw_data_processed", "processed", "processed_at"),
        Index("idx_raw_data_year_endpoint", "year", "endpoint"),
        Index("idx_raw_data_content_hash", "content_hash"),
        Index("idx_raw_data_request_id", "request_id"),
    )
    
    def __repr__(self):
        return f"<RawData(id={self.id}, endpoint={self.endpoint}, entity_id={self.entity_id})>"
    
    @property
    def display_name(self) -> str:
        """Get display name for the raw data record."""
        if self.entity_id:
            return f"{self.endpoint}:{self.entity_id}"
        return f"{self.endpoint}:{self.id}"
    
    @property
    def response_size(self) -> int:
        """Get response body size in characters."""
        if self.response_body:
            return len(str(self.response_body))
        return 0
    
    @property
    def is_large_response(self) -> bool:
        """Check if response is considered large (>10KB)."""
        return self.response_size > 10240  # 10KB
    
    @property
    def processing_status_display(self) -> str:
        """Get human-readable processing status."""
        status_map = {
            "pending": "Pending",
            "success": "Successfully Processed",
            "error": "Processing Error",
            "skipped": "Skipped",
        }
        return status_map.get(self.processed, self.processed or "Unknown")
    
    @property
    def age_hours(self) -> Optional[int]:
        """Get age of the record in hours."""
        if not self.request_timestamp:
            return None
        
        now = datetime.utcnow()
        delta = now - self.request_timestamp.replace(tzinfo=None)
        return int(delta.total_seconds() / 3600)
    
    def get_response_data(self) -> Dict[str, Any]:
        """Get response body as dictionary."""
        if isinstance(self.response_body, dict):
            return self.response_body
        return {}
    
    def get_entity_data(self) -> Optional[Dict[str, Any]]:
        """Extract entity data from response body."""
        response_data = self.get_response_data()
        
        # Handle different response structures
        if "items" in response_data and isinstance(response_data["items"], list):
            # Paginated response
            if response_data["items"]:
                return response_data["items"][0]  # Return first item
        elif "data" in response_data:
            # GraphQL response
            return response_data["data"]
        else:
            # Direct entity response
            return response_data
        
        return None
    
    def mark_as_processed(self, success: bool = True, error_message: str = None):
        """Mark record as processed."""
        self.processed = "success" if success else "error"
        self.processed_at = datetime.utcnow()
        if error_message:
            self.processing_error = error_message
    
    def mark_as_skipped(self, reason: str = None):
        """Mark record as skipped."""
        self.processed = "skipped"
        self.processed_at = datetime.utcnow()
        if reason:
            self.processing_error = f"Skipped: {reason}" 