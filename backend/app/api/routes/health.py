"""
Health check endpoints.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from app.core.database import get_async_session
from app.core.config import get_settings
from app.schemas.base import HealthResponse, StatsResponse

router = APIRouter()


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    Returns simple OK status for load balancer checks.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )


@router.get("/ready", response_model=HealthResponse)
async def readiness_check(
    db: AsyncSession = Depends(get_async_session)
):
    """
    Readiness check - verifies all dependencies are available.
    Used by Kubernetes readiness probes.
    """
    start_time = time.time()
    checks = {}
    overall_status = "healthy"
    
    try:
        # Database connectivity check
        try:
            result = await db.execute(text("SELECT 1"))
            await result.fetchone()
            checks["database"] = {
                "status": "healthy",
                "response_time": round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            checks["database"] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time": round((time.time() - start_time) * 1000, 2)
            }
            overall_status = "unhealthy"
        
        # Redis connectivity check
        try:
            settings = get_settings()
            redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            redis_start = time.time()
            await redis_client.ping()
            await redis_client.close()
            
            checks["redis"] = {
                "status": "healthy",
                "response_time": round((time.time() - redis_start) * 1000, 2)
            }
        except Exception as e:
            checks["redis"] = {
                "status": "unhealthy", 
                "error": str(e),
                "response_time": round((time.time() - start_time) * 1000, 2)
            }
            overall_status = "unhealthy"
            
    except Exception as e:
        overall_status = "unhealthy"
        checks["general"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    response = HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        checks=checks,
        response_time=round((time.time() - start_time) * 1000, 2)
    )
    
    if overall_status == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.dict()
        )
    
    return response


@router.get("/live", response_model=HealthResponse)
async def liveness_check():
    """
    Liveness check - verifies the application is running.
    Used by Kubernetes liveness probes.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        uptime=time.time()  # Simple uptime indicator
    )


@router.get("/detailed", response_model=Dict[str, Any])
async def detailed_health_check(
    db: AsyncSession = Depends(get_async_session)
):
    """
    Detailed health check with system metrics.
    Includes database stats, memory usage, and performance metrics.
    """
    start_time = time.time()
    health_data = {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0",
        "environment": get_settings().ENVIRONMENT,
        "checks": {},
        "metrics": {}
    }
    
    try:
        # Database health and stats
        try:
            # Basic connectivity
            await db.execute(text("SELECT 1"))
            
            # Get database statistics
            stats_queries = {
                "active_connections": "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'",
                "database_size": "SELECT pg_size_pretty(pg_database_size(current_database()))",
                "table_count": """
                    SELECT count(*) FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """,
                "uptime": "SELECT date_trunc('second', now() - pg_postmaster_start_time())"
            }
            
            db_metrics = {}
            for metric, query in stats_queries.items():
                try:
                    result = await db.execute(text(query))
                    value = await result.fetchone()
                    db_metrics[metric] = value[0] if value else None
                except Exception as e:
                    db_metrics[metric] = f"Error: {str(e)}"
            
            health_data["checks"]["database"] = {
                "status": "healthy",
                "metrics": db_metrics
            }
            
        except Exception as e:
            health_data["checks"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_data["status"] = "degraded"
        
        # Redis health and stats
        try:
            settings = get_settings()
            redis_client = redis.from_url(settings.REDIS_URL)
            
            await redis_client.ping()
            info = await redis_client.info()
            
            redis_metrics = {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "redis_version": info.get("redis_version", "unknown"),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0)
            }
            
            await redis_client.close()
            
            health_data["checks"]["redis"] = {
                "status": "healthy",
                "metrics": redis_metrics
            }
            
        except Exception as e:
            health_data["checks"]["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_data["status"] = "degraded"
        
        # Application metrics
        health_data["metrics"] = {
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "memory_usage": "N/A",  # Would implement with psutil in production
            "cpu_usage": "N/A",     # Would implement with psutil in production
            "disk_usage": "N/A"     # Would implement with psutil in production
        }
        
    except Exception as e:
        health_data["status"] = "unhealthy"
        health_data["error"] = str(e)
    
    # Return appropriate HTTP status
    if health_data["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_data
        )
    elif health_data["status"] == "degraded":
        raise HTTPException(
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            detail=health_data
        )
    
    return health_data


@router.get("/stats", response_model=StatsResponse)
async def system_stats(
    db: AsyncSession = Depends(get_async_session)
):
    """
    System statistics endpoint.
    Returns high-level statistics about data and system performance.
    """
    try:
        stats = {}
        
        # Data statistics
        data_queries = {
            "total_procurements": "SELECT COUNT(*) FROM procurements",
            "total_contracts": "SELECT COUNT(*) FROM contracts", 
            "total_participants": "SELECT COUNT(*) FROM participants",
            "total_lots": "SELECT COUNT(*) FROM lots",
            "active_procurements": "SELECT COUNT(*) FROM procurements WHERE status_id IN (SELECT id FROM statuses WHERE code IN ('active', 'published'))",
            "recent_procurements": "SELECT COUNT(*) FROM procurements WHERE created_at > NOW() - INTERVAL '7 days'"
        }
        
        for stat_name, query in data_queries.items():
            try:
                result = await db.execute(text(query))
                value = await result.fetchone()
                stats[stat_name] = value[0] if value else 0
            except Exception:
                stats[stat_name] = 0
        
        # Add calculated metrics
        stats["data_freshness_hours"] = 0  # Would calculate from last ingest
        stats["system_load"] = "normal"     # Would calculate from metrics
        stats["api_response_time"] = "normal"  # Would calculate from logs
        
        return StatsResponse(
            stats=stats,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate statistics: {str(e)}"
        ) 