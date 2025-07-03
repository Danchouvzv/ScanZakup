"""
Database models for ScanZakup.
"""

# Import all models for proper SQLAlchemy registration
from .base import BaseModel
from .trd_buy import Procurement 
from .lot import Lot
from .contract import Contract
from .participant import Participant
from .raw_data import RawDataTrdBuy, RawDataLot, RawDataContract, RawDataParticipant

__all__ = [
    "BaseModel",
    "Procurement", 
    "Lot",
    "Contract",
    "Participant",
    "RawDataTrdBuy",
    "RawDataLot", 
    "RawDataContract",
    "RawDataParticipant",
] 