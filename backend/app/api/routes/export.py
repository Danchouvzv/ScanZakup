"""
Export endpoints for data exports and report generation.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from celery.result import AsyncResult

from app.core.database import get_async_session
from app.schemas.export import (
    ExportRequest,
    ExportResponse,
    ExportStatus,
    ExportFormat,
    ReportRequest,
    ReportResponse
)
from app.api.routes.auth import optional_user
from app.services.export_service import ExportService
from app.core.celery_app import celery_app

router = APIRouter()


@router.post("/procurements", response_model=ExportResponse)
async def export_procurements(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Export procurement data to various formats.
    """
    try:
        export_service = ExportService(db)
        
        # Validate export request
        validation_result = await export_service.validate_export_request(
            export_type="procurements",
            filters=request.filters,
            max_rows=request.max_rows
        )
        
        if not validation_result["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_result["error"]
            )
        
        # For small exports, process immediately
        estimated_rows = validation_result.get("estimated_rows", 0)
        if estimated_rows <= 1000:
            # Process synchronously for small datasets
            file_path = await export_service.export_procurements(
                format=request.format,
                filters=request.filters,
                max_rows=request.max_rows
            )
            
            return ExportResponse(
                export_id=f"sync_{datetime.utcnow().timestamp()}",
                status="completed",
                format=request.format,
                file_path=file_path,
                file_size=0,  # Would calculate actual file size
                rows_exported=estimated_rows,
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                expires_at=datetime.utcnow().replace(hour=23, minute=59, second=59),
                download_url=f"/api/v1/export/download/{file_path.split('/')[-1]}"
            )
        else:
            # Process asynchronously for large datasets
            task = celery_app.send_task(
                "export_procurements_task",
                args=[request.dict(), current_user.get("id") if current_user else None]
            )
            
            return ExportResponse(
                export_id=task.id,
                status="pending",
                format=request.format,
                estimated_rows=estimated_rows,
                created_at=datetime.utcnow(),
                message="Export started. You will be notified when it's ready."
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start export: {str(e)}"
        )


@router.post("/lots", response_model=ExportResponse)
async def export_lots(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Export lot data to various formats.
    """
    try:
        export_service = ExportService(db)
        
        # Validate export request
        validation_result = await export_service.validate_export_request(
            export_type="lots",
            filters=request.filters,
            max_rows=request.max_rows
        )
        
        if not validation_result["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_result["error"]
            )
        
        # Process asynchronously
        task = celery_app.send_task(
            "export_lots_task",
            args=[request.dict(), current_user.get("id") if current_user else None]
        )
        
        return ExportResponse(
            export_id=task.id,
            status="pending",
            format=request.format,
            estimated_rows=validation_result.get("estimated_rows", 0),
            created_at=datetime.utcnow(),
            message="Export started. Check status for progress updates."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start export: {str(e)}"
        )


@router.post("/contracts", response_model=ExportResponse)
async def export_contracts(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Export contract data to various formats.
    """
    try:
        export_service = ExportService(db)
        
        # Validate export request
        validation_result = await export_service.validate_export_request(
            export_type="contracts",
            filters=request.filters,
            max_rows=request.max_rows
        )
        
        if not validation_result["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_result["error"]
            )
        
        # Process asynchronously
        task = celery_app.send_task(
            "export_contracts_task",
            args=[request.dict(), current_user.get("id") if current_user else None]
        )
        
        return ExportResponse(
            export_id=task.id,
            status="pending",
            format=request.format,
            estimated_rows=validation_result.get("estimated_rows", 0),
            created_at=datetime.utcnow(),
            message="Export started. Download will be available when ready."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start export: {str(e)}"
        )


@router.post("/participants", response_model=ExportResponse)
async def export_participants(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Export participant/supplier data to various formats.
    """
    try:
        export_service = ExportService(db)
        
        # Validate export request
        validation_result = await export_service.validate_export_request(
            export_type="participants",
            filters=request.filters,
            max_rows=request.max_rows
        )
        
        if not validation_result["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_result["error"]
            )
        
        # Process asynchronously
        task = celery_app.send_task(
            "export_participants_task",
            args=[request.dict(), current_user.get("id") if current_user else None]
        )
        
        return ExportResponse(
            export_id=task.id,
            status="pending",
            format=request.format,
            estimated_rows=validation_result.get("estimated_rows", 0),
            created_at=datetime.utcnow(),
            message="Export processing started. Check status for updates."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start export: {str(e)}"
        )


@router.get("/status/{export_id}", response_model=ExportStatus)
async def get_export_status(
    export_id: str,
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Get the status of an export job.
    """
    try:
        # Get task result from Celery
        result = AsyncResult(export_id, app=celery_app)
        
        if result.state == "PENDING":
            status = "pending"
            progress = 0
            message = "Export is queued for processing"
            file_path = None
            download_url = None
        elif result.state == "PROGRESS":
            status = "processing"
            progress = result.info.get("progress", 0)
            message = result.info.get("message", "Processing export...")
            file_path = None
            download_url = None
        elif result.state == "SUCCESS":
            status = "completed"
            progress = 100
            message = "Export completed successfully"
            file_path = result.result.get("file_path")
            download_url = f"/api/v1/export/download/{file_path.split('/')[-1]}" if file_path else None
        elif result.state == "FAILURE":
            status = "failed"
            progress = 0
            message = f"Export failed: {str(result.info)}"
            file_path = None
            download_url = None
        else:
            status = "unknown"
            progress = 0
            message = f"Unknown status: {result.state}"
            file_path = None
            download_url = None
        
        return ExportStatus(
            export_id=export_id,
            status=status,
            progress=progress,
            message=message,
            file_path=file_path,
            download_url=download_url,
            updated_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get export status: {str(e)}"
        )


@router.get("/download/{filename}")
async def download_export_file(
    filename: str,
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Download an exported file.
    """
    try:
        # Security check - ensure filename is safe
        if ".." in filename or "/" in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename"
            )
        
        # Construct file path (would be configurable)
        file_path = f"/app/exports/{filename}"
        
        # Check if file exists
        import os
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not found or has expired"
            )
        
        # Return file response
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        )


@router.post("/reports/analytics", response_model=ReportResponse)
async def generate_analytics_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Generate comprehensive analytics report.
    """
    try:
        # Process asynchronously
        task = celery_app.send_task(
            "generate_analytics_report_task",
            args=[request.dict(), current_user.get("id") if current_user else None]
        )
        
        return ReportResponse(
            report_id=task.id,
            status="pending",
            report_type="analytics",
            format=request.format,
            created_at=datetime.utcnow(),
            message="Analytics report generation started. This may take several minutes."
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start report generation: {str(e)}"
        )


@router.post("/reports/procurement-summary", response_model=ReportResponse)
async def generate_procurement_summary_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Generate procurement summary report.
    """
    try:
        # Process asynchronously
        task = celery_app.send_task(
            "generate_procurement_summary_report_task",
            args=[request.dict(), current_user.get("id") if current_user else None]
        )
        
        return ReportResponse(
            report_id=task.id,
            status="pending",
            report_type="procurement_summary",
            format=request.format,
            created_at=datetime.utcnow(),
            message="Procurement summary report generation started."
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start report generation: {str(e)}"
        )


@router.post("/reports/market-analysis", response_model=ReportResponse)
async def generate_market_analysis_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Generate market analysis report.
    """
    try:
        # Process asynchronously
        task = celery_app.send_task(
            "generate_market_analysis_report_task",
            args=[request.dict(), current_user.get("id") if current_user else None]
        )
        
        return ReportResponse(
            report_id=task.id,
            status="pending",
            report_type="market_analysis",
            format=request.format,
            created_at=datetime.utcnow(),
            message="Market analysis report generation started."
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start report generation: {str(e)}"
        )


@router.get("/reports/status/{report_id}", response_model=ReportResponse)
async def get_report_status(
    report_id: str,
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Get the status of a report generation job.
    """
    try:
        # Get task result from Celery
        result = AsyncResult(report_id, app=celery_app)
        
        if result.state == "PENDING":
            status = "pending"
            progress = 0
            message = "Report is queued for generation"
            file_path = None
            download_url = None
        elif result.state == "PROGRESS":
            status = "processing"
            progress = result.info.get("progress", 0)
            message = result.info.get("message", "Generating report...")
            file_path = None
            download_url = None
        elif result.state == "SUCCESS":
            status = "completed"
            progress = 100
            message = "Report generated successfully"
            file_path = result.result.get("file_path")
            download_url = f"/api/v1/export/download/{file_path.split('/')[-1]}" if file_path else None
        elif result.state == "FAILURE":
            status = "failed"
            progress = 0
            message = f"Report generation failed: {str(result.info)}"
            file_path = None
            download_url = None
        else:
            status = "unknown"
            progress = 0
            message = f"Unknown status: {result.state}"
            file_path = None
            download_url = None
        
        return ReportResponse(
            report_id=report_id,
            status=status,
            progress=progress,
            message=message,
            file_path=file_path,
            download_url=download_url,
            updated_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get report status: {str(e)}"
        )


@router.get("/formats")
async def get_supported_formats():
    """
    Get list of supported export formats.
    """
    return {
        "formats": [
            {
                "id": "csv",
                "name": "CSV",
                "description": "Comma-separated values",
                "mime_type": "text/csv",
                "extension": ".csv"
            },
            {
                "id": "xlsx",
                "name": "Excel",
                "description": "Microsoft Excel format",
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "extension": ".xlsx"
            },
            {
                "id": "json",
                "name": "JSON",
                "description": "JavaScript Object Notation",
                "mime_type": "application/json",
                "extension": ".json"
            },
            {
                "id": "xml",
                "name": "XML",
                "description": "Extensible Markup Language",
                "mime_type": "application/xml",
                "extension": ".xml"
            },
            {
                "id": "pdf",
                "name": "PDF",
                "description": "Portable Document Format (reports only)",
                "mime_type": "application/pdf",
                "extension": ".pdf"
            }
        ]
    }


@router.delete("/cleanup/{export_id}")
async def cleanup_export(
    export_id: str,
    current_user: Optional[dict] = Depends(optional_user)
):
    """
    Clean up export files and task data.
    """
    try:
        # Revoke task if still running
        celery_app.control.revoke(export_id, terminate=True)
        
        # TODO: Clean up associated files
        # This would remove files from storage
        
        return {"message": "Export cleanup completed", "export_id": export_id}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup export: {str(e)}"
        ) 