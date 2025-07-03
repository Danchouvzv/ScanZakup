"""
Celery tasks for background data processing.

Production-grade async tasks with proper error handling, retry logic, and monitoring.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import structlog
from celery import shared_task
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.services import (
    SyncService,
    TrdBuyService,
    LotService,
    ContractService,
    ParticipantService,
    AnalyticsService,
)
from app.core.monitoring import track_task_execution

logger = structlog.get_logger()


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    name="sync_all_data"
)
@track_task_execution
def sync_all_data(self, years: Optional[list] = None, force: bool = False) -> Dict[str, Any]:
    """
    Sync all data from Goszakup API.
    
    Args:
        years: List of years to sync. Defaults to current and previous year.
        force: Force full sync instead of incremental.
        
    Returns:
        Dict with sync results and statistics.
    """
    task_id = self.request.id
    logger.info("Starting full data sync", task_id=task_id, years=years, force=force)
    
    try:
        # Default to current and previous year
        if not years:
            current_year = datetime.now().year
            years = [current_year, current_year - 1]
        
        async def _sync_all():
            async with get_async_session() as session:
                sync_service = SyncService(session)
                results = {}
                
                for year in years:
                    logger.info("Syncing year", year=year, task_id=task_id)
                    year_result = await sync_service.sync_all(
                        year=year,
                        force_full=force
                    )
                    results[f"year_{year}"] = year_result
                
                return results
        
        # Use asyncio.run() for cleaner async handling
        results = asyncio.run(_sync_all())
        
        logger.info("Completed full data sync", task_id=task_id, results=results)
        return {
            "status": "success",
            "task_id": task_id,
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as exc:
        logger.error("Full data sync failed", task_id=task_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 30},
    name="sync_delta_data"
)
@track_task_execution
def sync_delta_data(self, hours_back: int = 2) -> Dict[str, Any]:
    """
    Sync delta data (recent changes only).
    
    Args:
        hours_back: How many hours back to sync changes.
        
    Returns:
        Dict with sync results.
    """
    task_id = self.request.id
    logger.info("Starting delta sync", task_id=task_id, hours_back=hours_back)
    
    try:
        async def _sync_delta():
            async with get_async_session() as session:
                sync_service = SyncService(session)
                
                # Sync recent TrdBuy data
                trd_buy_result = await sync_service.sync_trd_buy(
                    year=datetime.now().year,
                    force_full=False,
                    batch_size=100
                )
                
                # Sync recent contracts
                contracts_result = await sync_service.sync_contracts(
                    year=datetime.now().year,
                    force_full=False,
                    batch_size=100
                )
                
                return {
                    "trd_buy": trd_buy_result,
                    "contracts": contracts_result,
                }
        
        results = asyncio.run(_sync_delta())
        
        logger.info("Completed delta sync", task_id=task_id, results=results)
        return {
            "status": "success",
            "task_id": task_id,
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as exc:
        logger.error("Delta sync failed", task_id=task_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 120},
    name="sync_trd_buy_data"
)
@track_task_execution
def sync_trd_buy_data(self, year: int, force: bool = False, batch_size: int = 1000) -> Dict[str, Any]:
    """
    Sync TrdBuy (procurement announcements) data.
    
    Args:
        year: Year to sync.
        force: Force full sync.
        batch_size: Batch size for processing.
        
    Returns:
        Dict with sync results.
    """
    task_id = self.request.id
    logger.info("Starting TrdBuy sync", task_id=task_id, year=year, force=force)
    
    try:
        async def _sync_trd_buy():
            async with get_async_session() as session:
                sync_service = SyncService(session)
                return await sync_service.sync_trd_buy(
                    year=year,
                    force_full=force,
                    batch_size=batch_size
                )
        
        result = asyncio.run(_sync_trd_buy())
        
        logger.info("Completed TrdBuy sync", task_id=task_id, result=result)
        return {
            "status": "success",
            "task_id": task_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as exc:
        logger.error("TrdBuy sync failed", task_id=task_id, error=str(exc))
        raise self.retry(exc=exc, countdown=120 * (self.request.retries + 1))


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 120},
    name="sync_lots_data"
)
@track_task_execution
def sync_lots_data(self, year: int, force: bool = False, batch_size: int = 1000) -> Dict[str, Any]:
    """
    Sync lots data.
    
    Args:
        year: Year to sync.
        force: Force full sync.
        batch_size: Batch size for processing.
        
    Returns:
        Dict with sync results.
    """
    task_id = self.request.id
    logger.info("Starting lots sync", task_id=task_id, year=year, force=force)
    
    try:
        async def _sync_lots():
            async with get_async_session() as session:
                sync_service = SyncService(session)
                return await sync_service.sync_lots(
                    year=year,
                    force_full=force,
                    batch_size=batch_size
                )
        
        result = asyncio.run(_sync_lots())
        
        logger.info("Completed lots sync", task_id=task_id, result=result)
        return {
            "status": "success",
            "task_id": task_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as exc:
        logger.error("Lots sync failed", task_id=task_id, error=str(exc))
        raise self.retry(exc=exc, countdown=120 * (self.request.retries + 1))


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 120},
    name="sync_contracts_data"
)
@track_task_execution
def sync_contracts_data(self, year: int, force: bool = False, batch_size: int = 1000) -> Dict[str, Any]:
    """
    Sync contracts data.
    
    Args:
        year: Year to sync.
        force: Force full sync.
        batch_size: Batch size for processing.
        
    Returns:
        Dict with sync results.
    """
    task_id = self.request.id
    logger.info("Starting contracts sync", task_id=task_id, year=year, force=force)
    
    try:
        async def _sync_contracts():
            async with get_async_session() as session:
                sync_service = SyncService(session)
                return await sync_service.sync_contracts(
                    year=year,
                    force_full=force,
                    batch_size=batch_size
                )
        
        result = asyncio.run(_sync_contracts())
        
        logger.info("Completed contracts sync", task_id=task_id, result=result)
        return {
            "status": "success",
            "task_id": task_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as exc:
        logger.error("Contracts sync failed", task_id=task_id, error=str(exc))
        raise self.retry(exc=exc, countdown=120 * (self.request.retries + 1))


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 300},
    name="sync_participants_data"
)
@track_task_execution
def sync_participants_data(self, year: int, force: bool = False, batch_size: int = 500) -> Dict[str, Any]:
    """
    Sync participants data.
    
    Args:
        year: Year to sync.
        force: Force full sync.
        batch_size: Batch size for processing.
        
    Returns:
        Dict with sync results.
    """
    task_id = self.request.id
    logger.info("Starting participants sync", task_id=task_id, year=year, force=force)
    
    try:
        async def _sync_participants():
            async with get_async_session() as session:
                sync_service = SyncService(session)
                return await sync_service.sync_participants(
                    year=year,
                    force_full=force,
                    batch_size=batch_size
                )
        
        result = asyncio.run(_sync_participants())
        
        logger.info("Completed participants sync", task_id=task_id, result=result)
        return {
            "status": "success",
            "task_id": task_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as exc:
        logger.error("Participants sync failed", task_id=task_id, error=str(exc))
        raise self.retry(exc=exc, countdown=300 * (self.request.retries + 1))


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 600},
    name="cleanup_old_data"
)
@track_task_execution
def cleanup_old_data(self, days_old: int = 365) -> Dict[str, Any]:
    """
    Clean up old data and optimize database.
    
    Args:
        days_old: Remove data older than this many days.
        
    Returns:
        Dict with cleanup results.
    """
    task_id = self.request.id
    logger.info("Starting data cleanup", task_id=task_id, days_old=days_old)
    
    try:
        async def _cleanup():
            async with get_async_session() as session:
                # Calculate cutoff date
                cutoff_date = datetime.utcnow() - timedelta(days=days_old)
                
                # Clean up sync logs - SQLAlchemy 2.0 style
                from app.models import SyncLog
                sync_stmt = delete(SyncLog).where(SyncLog.timestamp < cutoff_date)
                sync_result = await session.execute(sync_stmt)
                
                # Clean up old analytics cache - SQLAlchemy 2.0 style
                from app.models import AnalyticsCache
                analytics_stmt = delete(AnalyticsCache).where(AnalyticsCache.created_at < cutoff_date)
                analytics_result = await session.execute(analytics_stmt)
                
                await session.commit()
                
                return {
                    "sync_logs_deleted": sync_result.rowcount,
                    "analytics_cache_deleted": analytics_result.rowcount,
                    "cutoff_date": cutoff_date.isoformat(),
                }
        
        result = asyncio.run(_cleanup())
        
        logger.info("Completed data cleanup", task_id=task_id, result=result)
        return {
            "status": "success",
            "task_id": task_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as exc:
        logger.error("Data cleanup failed", task_id=task_id, error=str(exc))
        raise self.retry(exc=exc, countdown=600 * (self.request.retries + 1))


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 1, "countdown": 300},
    name="health_check"
)
@track_task_execution
def health_check(self) -> Dict[str, Any]:
    """
    Perform system health check.
    
    Returns:
        Dict with health check results.
    """
    task_id = self.request.id
    logger.info("Starting health check", task_id=task_id)
    
    try:
        async def _health_check():
            async with get_async_session() as session:
                checks = {}
                
                # Database connectivity
                try:
                    await session.execute(select(1))
                    checks["database"] = {"status": "healthy", "latency_ms": 0}
                except Exception as e:
                    checks["database"] = {"status": "unhealthy", "error": str(e)}
                
                # Data freshness check
                try:
                    sync_service = SyncService(session)
                    last_sync = await sync_service.get_last_sync_time()
                    if last_sync:
                        hours_since_sync = (datetime.utcnow() - last_sync).total_seconds() / 3600
                        if hours_since_sync < 2:
                            checks["data_freshness"] = {"status": "healthy", "hours_since_sync": hours_since_sync}
                        else:
                            checks["data_freshness"] = {"status": "stale", "hours_since_sync": hours_since_sync}
                    else:
                        checks["data_freshness"] = {"status": "no_data", "hours_since_sync": None}
                except Exception as e:
                    checks["data_freshness"] = {"status": "error", "error": str(e)}
                
                # Queue health
                checks["celery"] = {"status": "healthy", "task_id": task_id}
                
                overall_status = "healthy" if all(
                    check.get("status") == "healthy" 
                    for check in checks.values()
                ) else "degraded"
                
                return {
                    "overall_status": overall_status,
                    "checks": checks,
                }
        
        result = asyncio.run(_health_check())
        
        logger.info("Completed health check", task_id=task_id, result=result)
        return {
            "status": "success",
            "task_id": task_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as exc:
        logger.error("Health check failed", task_id=task_id, error=str(exc))
        raise self.retry(exc=exc, countdown=300)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 180},
    name="generate_analytics_report"
)
@track_task_execution
def generate_analytics_report(self, report_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate analytics report in background.
    
    Args:
        report_type: Type of report to generate.
        params: Parameters for report generation.
        
    Returns:
        Dict with report generation results.
    """
    task_id = self.request.id
    logger.info("Starting analytics report generation", 
                task_id=task_id, report_type=report_type, params=params)
    
    try:
        async def _generate_report():
            async with get_async_session() as session:
                analytics_service = AnalyticsService(session)
                
                if report_type == "procurement_trends":
                    return await analytics_service.get_market_trends(**params)
                elif report_type == "supplier_analysis":
                    return await analytics_service.get_supplier_performance_analysis(**params)
                elif report_type == "dashboard_summary":
                    return await analytics_service.get_dashboard_summary(**params)
                else:
                    raise ValueError(f"Unknown report type: {report_type}")
        
        result = asyncio.run(_generate_report())
        
        logger.info("Completed analytics report generation", task_id=task_id, report_type=report_type)
        return {
            "status": "success",
            "task_id": task_id,
            "report_type": report_type,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as exc:
        logger.error("Analytics report generation failed", 
                    task_id=task_id, report_type=report_type, error=str(exc))
        raise self.retry(exc=exc, countdown=180 * (self.request.retries + 1)) 