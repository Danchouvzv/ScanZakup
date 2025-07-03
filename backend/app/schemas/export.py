"""
Export schema models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field, validator

from .base import BaseSchema


class ExportFormat(str, Enum):
    """Supported export formats."""
    EXCEL = "excel"
    CSV = "csv"


class ExportStatus(str, Enum):
    """Export job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class ExportType(str, Enum):
    """Types of data that can be exported."""
    PROCUREMENTS = "procurements"
    LOTS = "lots"
    CONTRACTS = "contracts"
    PARTICIPANTS = "participants"
    ANALYTICS = "analytics"
    COMPREHENSIVE = "comprehensive"


class ExportRequest(BaseSchema):
    """Export request parameters."""
    
    # Export configuration
    export_type: ExportType = Field(description="Type of data to export")
    format: ExportFormat = Field(default=ExportFormat.EXCEL, description="Export format")
    filename: Optional[str] = Field(None, description="Custom filename (without extension)")
    
    # Data filtering
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters to apply to the data")
    columns: Optional[List[str]] = Field(None, description="Specific columns to include")
    
    # Export options
    max_rows: Optional[int] = Field(None, description="Maximum number of rows to export")
    include_headers: bool = Field(True, description="Include column headers")
    include_metadata: bool = Field(True, description="Include export metadata sheet")
    
    # Date range (if applicable)
    date_from: Optional[datetime] = Field(None, description="Start date for data range")
    date_to: Optional[datetime] = Field(None, description="End date for data range")
    
    # Notification options
    email_on_completion: bool = Field(False, description="Send email when export is ready")
    email_address: Optional[str] = Field(None, description="Email address for notifications")
    
    @validator('email_address')
    def validate_email_when_notification_enabled(cls, v, values):
        """Validate email is provided when notifications are enabled."""
        if values.get('email_on_completion') and not v:
            raise ValueError('Email address required when email_on_completion is True')
        return v
    
    @validator('filename')
    def validate_filename(cls, v):
        """Validate filename format."""
        if v and ('/' in v or '\\' in v):
            raise ValueError('Filename cannot contain path separators')
        return v


class ExportJob(BaseSchema):
    """Export job information."""
    
    # Job identification
    id: str = Field(description="Unique export job ID")
    export_type: ExportType = Field(description="Type of data being exported")
    format: ExportFormat = Field(description="Export format")
    
    # Job status
    status: ExportStatus = Field(description="Current job status")
    progress: Optional[int] = Field(None, description="Progress percentage (0-100)")
    
    # Request details
    requested_by: Optional[str] = Field(None, description="User who requested the export")
    request_parameters: Dict[str, Any] = Field(description="Original request parameters")
    
    # Timing information
    created_at: datetime = Field(description="When the job was created")
    started_at: Optional[datetime] = Field(None, description="When processing started")
    completed_at: Optional[datetime] = Field(None, description="When processing completed")
    expires_at: Optional[datetime] = Field(None, description="When the export file expires")
    
    # Results
    file_info: Optional['ExportFileInfo'] = Field(None, description="File information when completed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    row_count: Optional[int] = Field(None, description="Number of rows exported")
    
    # Metadata
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")


class ExportFileInfo(BaseSchema):
    """Information about exported file."""
    
    # File details
    filename: str = Field(description="Generated filename")
    file_size: int = Field(description="File size in bytes")
    file_path: Optional[str] = Field(None, description="Internal file path")
    
    # Download information
    download_url: Optional[str] = Field(None, description="Download URL")
    download_token: Optional[str] = Field(None, description="Download authorization token")
    download_expires: Optional[datetime] = Field(None, description="Download URL expiration")
    
    # Content information
    row_count: int = Field(description="Number of data rows")
    column_count: int = Field(description="Number of columns")
    sheet_count: Optional[int] = Field(None, description="Number of sheets (Excel only)")
    
    # Checksums for integrity
    md5_hash: Optional[str] = Field(None, description="MD5 hash of the file")
    sha256_hash: Optional[str] = Field(None, description="SHA256 hash of the file")
    
    # Creation info
    created_at: datetime = Field(description="When the file was created")
    format: ExportFormat = Field(description="File format")


class ExportStats(BaseSchema):
    """Export system statistics."""
    
    # Job counts
    total_jobs: int = Field(description="Total number of export jobs")
    pending_jobs: int = Field(description="Number of pending jobs")
    processing_jobs: int = Field(description="Number of currently processing jobs")
    completed_jobs: int = Field(description="Number of completed jobs")
    failed_jobs: int = Field(description="Number of failed jobs")
    
    # Performance metrics
    average_processing_time: float = Field(description="Average processing time in seconds")
    success_rate: float = Field(description="Success rate percentage")
    
    # Popular exports
    popular_export_types: List[Dict[str, Any]] = Field(description="Most requested export types")
    popular_formats: List[Dict[str, Any]] = Field(description="Most requested formats")
    
    # Resource usage
    total_files_generated: int = Field(description="Total files generated")
    total_data_exported: int = Field(description="Total rows exported")
    storage_used: int = Field(description="Storage used in bytes")
    
    # Time period
    period_start: datetime = Field(description="Statistics period start")
    period_end: datetime = Field(description="Statistics period end")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ExportHistory(BaseSchema):
    """User export history."""
    
    # User information
    user_id: Optional[str] = Field(None, description="User identifier")
    
    # Export summary
    total_exports: int = Field(description="Total number of exports")
    successful_exports: int = Field(description="Number of successful exports")
    failed_exports: int = Field(description="Number of failed exports")
    
    # Recent exports
    recent_jobs: List[ExportJob] = Field(description="Recent export jobs")
    
    # Usage patterns
    favorite_export_types: List[Dict[str, Any]] = Field(description="Most used export types")
    favorite_formats: List[Dict[str, Any]] = Field(description="Most used formats")
    
    # Time analysis
    first_export: Optional[datetime] = Field(None, description="Date of first export")
    last_export: Optional[datetime] = Field(None, description="Date of last export")
    most_active_period: Optional[str] = Field(None, description="Most active time period")
    
    # Generated at
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class BulkExportRequest(BaseSchema):
    """Request for multiple exports in batch."""
    
    # Batch information
    batch_name: Optional[str] = Field(None, description="Name for this batch")
    
    # Export requests
    exports: List[ExportRequest] = Field(description="List of export requests")
    
    # Batch options
    sequential_processing: bool = Field(False, description="Process exports sequentially")
    notify_on_completion: bool = Field(True, description="Notify when all exports complete")
    combine_results: bool = Field(False, description="Combine all exports into one file")
    
    # Scheduling
    schedule_at: Optional[datetime] = Field(None, description="Schedule batch for later")
    
    @validator('exports')
    def validate_exports_not_empty(cls, v):
        """Ensure at least one export is requested."""
        if not v:
            raise ValueError('At least one export must be specified')
        return v


class BulkExportJob(BaseSchema):
    """Bulk export job status."""
    
    # Batch identification
    batch_id: str = Field(description="Unique batch ID")
    batch_name: Optional[str] = Field(None, description="Batch name")
    
    # Batch status
    status: ExportStatus = Field(description="Overall batch status")
    progress: int = Field(description="Overall progress percentage")
    
    # Individual jobs
    individual_jobs: List[ExportJob] = Field(description="Status of individual exports")
    completed_jobs: int = Field(description="Number of completed jobs")
    failed_jobs: int = Field(description="Number of failed jobs")
    
    # Results
    combined_file: Optional[ExportFileInfo] = Field(None, description="Combined file if requested")
    individual_files: List[ExportFileInfo] = Field(description="Individual export files")
    
    # Timing
    created_at: datetime = Field(description="When batch was created")
    started_at: Optional[datetime] = Field(None, description="When processing started")
    completed_at: Optional[datetime] = Field(None, description="When batch completed")
    
    # Error handling
    error_summary: Optional[str] = Field(None, description="Summary of any errors")
    continue_on_error: bool = Field(True, description="Whether to continue if individual jobs fail")


# Update forward references
ExportJob.model_rebuild() 