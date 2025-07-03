"""
API package for ScanZakup.
"""

from fastapi import APIRouter

from app.api.routes import (
    health,
    auth,
    procurements,
    lots,
    contracts,
    participants,
    analytics,
    export
)

# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(procurements.router, prefix="/procurements", tags=["procurements"])
api_router.include_router(lots.router, prefix="/lots", tags=["lots"])
api_router.include_router(contracts.router, prefix="/contracts", tags=["contracts"])
api_router.include_router(participants.router, prefix="/participants", tags=["participants"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(export.router, prefix="/export", tags=["export"])

__all__ = ["api_router"] 