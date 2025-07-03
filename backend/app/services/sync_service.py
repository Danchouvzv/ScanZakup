"""
Synchronization Service

Handles data synchronization with Goszakup API, including:
- Incremental data loading
- Raw data management
- Data transformation and validation
- Sync metrics and monitoring
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4

import structlog
from sqlalchemy import and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.goszakup_client import GoszakupClient
from app.models.raw_data import RawData
from app.models.trd_buy import TrdBuy
from app.models.lot import Lot
from app.models.contract import Contract
from app.models.participant import Participant
from app.services.base_service import BaseService

logger = structlog.get_logger()


class SyncService:
    """
    Service for synchronizing data with Goszakup API.
    
    Features:
    - Incremental synchronization
    - Error handling and retry logic
    - Metrics collection
    - Data validation
    - Raw data backup
    """
    
    def __init__(self, session: AsyncSession = None):
        """Initialize sync service."""
        self._session = session
        self.client = GoszakupClient()
        
        # Services for each entity
        self.raw_service = BaseService(RawData, session)
        self.trd_buy_service = BaseService(TrdBuy, session)
        self.lot_service = BaseService(Lot, session)
        self.contract_service = BaseService(Contract, session)
        self.participant_service = BaseService(Participant, session)
    
    @property
    async def session(self) -> AsyncSession:
        """Get database session."""
        if self._session is None:
            self._session = await get_session()
        return self._session
    
    async def close(self):
        """Close resources."""
        await self.client.close()
        if self._session:
            await self._session.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    # Main Sync Methods
    
    async def sync_all(
        self,
        years: List[int] = None,
        force_full: bool = False,
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """
        Sync all data types for specified years.
        
        Args:
            years: Years to sync (defaults to current and previous year)
            force_full: Force full sync instead of incremental
            batch_size: Batch size for processing
            
        Returns:
            Sync results summary
        """
        if years is None:
            current_year = datetime.now().year
            years = [current_year - 1, current_year]
        
        logger.info("Starting full sync", years=years, force_full=force_full)
        
        sync_results = {
            "start_time": datetime.utcnow(),
            "years": years,
            "force_full": force_full,
            "results": {},
            "errors": [],
        }
        
        # Sync entities in order (participants first, then trd_buy, lots, contracts)
        entities = ["participants", "trd_buy", "lots", "contracts"]
        
        for entity in entities:
            entity_results = []
            
            for year in years:
                try:
                    logger.info(f"Syncing {entity} for {year}")
                    
                    if entity == "participants":
                        # Participants are not year-specific
                        if year == years[0]:  # Only sync once
                            result = await self.sync_participants(
                                force_full=force_full,
                                batch_size=batch_size
                            )
                            entity_results.append({"year": "all", "result": result})
                    else:
                        sync_method = getattr(self, f"sync_{entity}")
                        result = await sync_method(
                            year=year,
                            force_full=force_full,
                            batch_size=batch_size
                        )
                        entity_results.append({"year": year, "result": result})
                
                except Exception as e:
                    error_msg = f"Failed to sync {entity} for {year}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    sync_results["errors"].append(error_msg)
                    entity_results.append({"year": year, "error": str(e)})
            
            sync_results["results"][entity] = entity_results
        
        sync_results["end_time"] = datetime.utcnow()
        sync_results["duration"] = (
            sync_results["end_time"] - sync_results["start_time"]
        ).total_seconds()
        
        logger.info("Full sync completed", results=sync_results)
        return sync_results
    
    async def sync_trd_buy(
        self,
        year: int,
        force_full: bool = False,
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """
        Sync procurement announcements (trd_buy).
        
        Args:
            year: Year to sync
            force_full: Force full sync
            batch_size: Batch size for processing
            
        Returns:
            Sync results
        """
        logger.info("Starting trd_buy sync", year=year, force_full=force_full)
        
        start_time = datetime.utcnow()
        request_id = str(uuid4())
        
        # Determine sync parameters
        filters = {"year": year}
        if not force_full:
            last_sync = await self._get_last_sync_time("trd_buy", year)
            if last_sync:
                filters["updated_date"] = {"gte": last_sync.isoformat()}
        
        # Fetch data from API
        try:
            api_data = await self.client.trd_buy(**filters)
            logger.info(f"Fetched {len(api_data)} trd_buy records from API", year=year)
        except Exception as e:
            logger.error(f"Failed to fetch trd_buy data: {str(e)}", exc_info=True)
            return {"error": str(e), "processed": 0}
        
        # Store raw data
        await self.raw_service.create({
            "endpoint": "trd_buy",
            "request_id": request_id,
            "method": "GET",
            "url": "trd_buy",
            "query_params": filters,
            "response_body": {"items": api_data, "total": len(api_data)},
            "status_code": 200,
            "request_timestamp": start_time,
            "response_time_ms": 0,  # Will be updated
            "data_type": "trd_buy",
            "year": year,
            "api_version": "v2",
        })
        
        # Process data in batches
        processed = 0
        created = 0
        updated = 0
        errors = []
        
        for i in range(0, len(api_data), batch_size):
            batch = api_data[i:i + batch_size]
            
            try:
                batch_results = await self._process_trd_buy_batch(batch, year)
                processed += batch_results["processed"]
                created += batch_results["created"]
                updated += batch_results["updated"]
                errors.extend(batch_results["errors"])
                
                logger.info(
                    f"Processed trd_buy batch {i//batch_size + 1}",
                    batch_size=len(batch),
                    processed=batch_results["processed"],
                )
                
            except Exception as e:
                error_msg = f"Failed to process trd_buy batch {i//batch_size + 1}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
        
        # Update sync timestamp
        await self._update_sync_timestamp("trd_buy", year)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        results = {
            "entity": "trd_buy",
            "year": year,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
            "total_fetched": len(api_data),
            "processed": processed,
            "created": created,
            "updated": updated,
            "errors": errors,
            "request_id": request_id,
        }
        
        logger.info("trd_buy sync completed", results=results)
        return results
    
    async def sync_lots(
        self,
        year: int,
        force_full: bool = False,
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """
        Sync lots.
        
        Args:
            year: Year to sync
            force_full: Force full sync
            batch_size: Batch size for processing
            
        Returns:
            Sync results
        """
        logger.info("Starting lots sync", year=year, force_full=force_full)
        
        start_time = datetime.utcnow()
        request_id = str(uuid4())
        
        # Get trd_buy IDs for the year to sync lots
        session = await self.session
        trd_buy_ids = await session.execute(
            session.query(TrdBuy.goszakup_id)
            .filter(TrdBuy.year == year)
        )
        trd_buy_ids = [row[0] for row in trd_buy_ids.fetchall()]
        
        logger.info(f"Found {len(trd_buy_ids)} trd_buy records for lots sync", year=year)
        
        # Determine sync parameters
        filters = {"year": year}
        if not force_full:
            last_sync = await self._get_last_sync_time("lots", year)
            if last_sync:
                filters["updated_date"] = {"gte": last_sync.isoformat()}
        
        # Fetch data from API
        try:
            api_data = await self.client.lots(**filters)
            logger.info(f"Fetched {len(api_data)} lot records from API", year=year)
        except Exception as e:
            logger.error(f"Failed to fetch lots data: {str(e)}", exc_info=True)
            return {"error": str(e), "processed": 0}
        
        # Store raw data
        await self.raw_service.create({
            "endpoint": "lot",
            "request_id": request_id,
            "method": "GET",
            "url": "lot",
            "query_params": filters,
            "response_body": {"items": api_data, "total": len(api_data)},
            "status_code": 200,
            "request_timestamp": start_time,
            "response_time_ms": 0,
            "data_type": "lot",
            "year": year,
            "api_version": "v2",
        })
        
        # Process data in batches
        processed = 0
        created = 0
        updated = 0
        errors = []
        
        for i in range(0, len(api_data), batch_size):
            batch = api_data[i:i + batch_size]
            
            try:
                batch_results = await self._process_lots_batch(batch, year)
                processed += batch_results["processed"]
                created += batch_results["created"]
                updated += batch_results["updated"]
                errors.extend(batch_results["errors"])
                
                logger.info(
                    f"Processed lots batch {i//batch_size + 1}",
                    batch_size=len(batch),
                    processed=batch_results["processed"],
                )
                
            except Exception as e:
                error_msg = f"Failed to process lots batch {i//batch_size + 1}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
        
        # Update sync timestamp
        await self._update_sync_timestamp("lots", year)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        results = {
            "entity": "lots",
            "year": year,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
            "total_fetched": len(api_data),
            "processed": processed,
            "created": created,
            "updated": updated,
            "errors": errors,
            "request_id": request_id,
        }
        
        logger.info("Lots sync completed", results=results)
        return results
    
    async def sync_contracts(
        self,
        year: int,
        force_full: bool = False,
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """
        Sync contracts.
        
        Args:
            year: Year to sync
            force_full: Force full sync
            batch_size: Batch size for processing
            
        Returns:
            Sync results
        """
        logger.info("Starting contracts sync", year=year, force_full=force_full)
        
        start_time = datetime.utcnow()
        request_id = str(uuid4())
        
        # Determine sync parameters
        filters = {"year": year}
        if not force_full:
            last_sync = await self._get_last_sync_time("contracts", year)
            if last_sync:
                filters["updated_date"] = {"gte": last_sync.isoformat()}
        
        # Fetch data from API
        try:
            api_data = await self.client.contracts(**filters)
            logger.info(f"Fetched {len(api_data)} contract records from API", year=year)
        except Exception as e:
            logger.error(f"Failed to fetch contracts data: {str(e)}", exc_info=True)
            return {"error": str(e), "processed": 0}
        
        # Store raw data
        await self.raw_service.create({
            "endpoint": "contract",
            "request_id": request_id,
            "method": "GET",
            "url": "contract",
            "query_params": filters,
            "response_body": {"items": api_data, "total": len(api_data)},
            "status_code": 200,
            "request_timestamp": start_time,
            "response_time_ms": 0,
            "data_type": "contract",
            "year": year,
            "api_version": "v2",
        })
        
        # Process data in batches
        processed = 0
        created = 0
        updated = 0
        errors = []
        
        for i in range(0, len(api_data), batch_size):
            batch = api_data[i:i + batch_size]
            
            try:
                batch_results = await self._process_contracts_batch(batch, year)
                processed += batch_results["processed"]
                created += batch_results["created"]
                updated += batch_results["updated"]
                errors.extend(batch_results["errors"])
                
                logger.info(
                    f"Processed contracts batch {i//batch_size + 1}",
                    batch_size=len(batch),
                    processed=batch_results["processed"],
                )
                
            except Exception as e:
                error_msg = f"Failed to process contracts batch {i//batch_size + 1}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
        
        # Update sync timestamp
        await self._update_sync_timestamp("contracts", year)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        results = {
            "entity": "contracts",
            "year": year,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
            "total_fetched": len(api_data),
            "processed": processed,
            "created": created,
            "updated": updated,
            "errors": errors,
            "request_id": request_id,
        }
        
        logger.info("Contracts sync completed", results=results)
        return results
    
    async def sync_participants(
        self,
        force_full: bool = False,
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """
        Sync participants (suppliers and customers).
        
        Args:
            force_full: Force full sync
            batch_size: Batch size for processing
            
        Returns:
            Sync results
        """
        logger.info("Starting participants sync", force_full=force_full)
        
        start_time = datetime.utcnow()
        request_id = str(uuid4())
        
        # Determine sync parameters
        filters = {}
        if not force_full:
            last_sync = await self._get_last_sync_time("participants")
            if last_sync:
                filters["updated_date"] = {"gte": last_sync.isoformat()}
        
        # Fetch data from API
        try:
            api_data = await self.client.participants(**filters)
            logger.info(f"Fetched {len(api_data)} participant records from API")
        except Exception as e:
            logger.error(f"Failed to fetch participants data: {str(e)}", exc_info=True)
            return {"error": str(e), "processed": 0}
        
        # Store raw data
        await self.raw_service.create({
            "endpoint": "participant",
            "request_id": request_id,
            "method": "GET",
            "url": "participant",
            "query_params": filters,
            "response_body": {"items": api_data, "total": len(api_data)},
            "status_code": 200,
            "request_timestamp": start_time,
            "response_time_ms": 0,
            "data_type": "participant",
            "api_version": "v2",
        })
        
        # Process data in batches
        processed = 0
        created = 0
        updated = 0
        errors = []
        
        for i in range(0, len(api_data), batch_size):
            batch = api_data[i:i + batch_size]
            
            try:
                batch_results = await self._process_participants_batch(batch)
                processed += batch_results["processed"]
                created += batch_results["created"]
                updated += batch_results["updated"]
                errors.extend(batch_results["errors"])
                
                logger.info(
                    f"Processed participants batch {i//batch_size + 1}",
                    batch_size=len(batch),
                    processed=batch_results["processed"],
                )
                
            except Exception as e:
                error_msg = f"Failed to process participants batch {i//batch_size + 1}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
        
        # Update sync timestamp
        await self._update_sync_timestamp("participants")
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        results = {
            "entity": "participants",
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
            "total_fetched": len(api_data),
            "processed": processed,
            "created": created,
            "updated": updated,
            "errors": errors,
            "request_id": request_id,
        }
        
        logger.info("Participants sync completed", results=results)
        return results
    
    # Batch Processing Methods
    
    async def _process_trd_buy_batch(self, batch: List[dict], year: int) -> Dict[str, Any]:
        """Process a batch of trd_buy records."""
        processed = 0
        created = 0
        updated = 0
        errors = []
        
        for item in batch:
            try:
                # Transform API data to model format
                model_data = self._transform_trd_buy_data(item)
                model_data["year"] = year
                
                # Check if record exists
                existing = await self.trd_buy_service.get_by_field(
                    "goszakup_id", 
                    model_data["goszakup_id"]
                )
                
                if existing:
                    # Update existing record
                    await self.trd_buy_service.update(existing.id, model_data)
                    updated += 1
                else:
                    # Create new record
                    await self.trd_buy_service.create(model_data)
                    created += 1
                
                processed += 1
                
            except Exception as e:
                error_msg = f"Failed to process trd_buy {item.get('id', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        return {
            "processed": processed,
            "created": created,
            "updated": updated,
            "errors": errors,
        }
    
    async def _process_lots_batch(self, batch: List[dict], year: int) -> Dict[str, Any]:
        """Process a batch of lot records."""
        processed = 0
        created = 0
        updated = 0
        errors = []
        
        for item in batch:
            try:
                # Transform API data to model format
                model_data = self._transform_lot_data(item)
                
                # Check if record exists
                existing = await self.lot_service.get_by_field(
                    "goszakup_id", 
                    model_data["goszakup_id"]
                )
                
                if existing:
                    # Update existing record
                    await self.lot_service.update(existing.id, model_data)
                    updated += 1
                else:
                    # Create new record
                    await self.lot_service.create(model_data)
                    created += 1
                
                processed += 1
                
            except Exception as e:
                error_msg = f"Failed to process lot {item.get('id', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        return {
            "processed": processed,
            "created": created,
            "updated": updated,
            "errors": errors,
        }
    
    async def _process_contracts_batch(self, batch: List[dict], year: int) -> Dict[str, Any]:
        """Process a batch of contract records."""
        processed = 0
        created = 0
        updated = 0
        errors = []
        
        for item in batch:
            try:
                # Transform API data to model format
                model_data = self._transform_contract_data(item)
                model_data["year"] = year
                
                # Check if record exists
                existing = await self.contract_service.get_by_field(
                    "goszakup_id", 
                    model_data["goszakup_id"]
                )
                
                if existing:
                    # Update existing record
                    await self.contract_service.update(existing.id, model_data)
                    updated += 1
                else:
                    # Create new record
                    await self.contract_service.create(model_data)
                    created += 1
                
                processed += 1
                
            except Exception as e:
                error_msg = f"Failed to process contract {item.get('id', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        return {
            "processed": processed,
            "created": created,
            "updated": updated,
            "errors": errors,
        }
    
    async def _process_participants_batch(self, batch: List[dict]) -> Dict[str, Any]:
        """Process a batch of participant records."""
        processed = 0
        created = 0
        updated = 0
        errors = []
        
        for item in batch:
            try:
                # Transform API data to model format
                model_data = self._transform_participant_data(item)
                
                # Check if record exists (by BIN or IIN)
                identifier = model_data.get("bin") or model_data.get("iin")
                if not identifier:
                    errors.append(f"Participant missing BIN/IIN: {item}")
                    continue
                
                existing = await self.participant_service.get_by_field("bin", identifier)
                if not existing and model_data.get("iin"):
                    existing = await self.participant_service.get_by_field("iin", model_data["iin"])
                
                if existing:
                    # Update existing record
                    await self.participant_service.update(existing.id, model_data)
                    updated += 1
                else:
                    # Create new record
                    await self.participant_service.create(model_data)
                    created += 1
                
                processed += 1
                
            except Exception as e:
                error_msg = f"Failed to process participant {item.get('bin', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        return {
            "processed": processed,
            "created": created,
            "updated": updated,
            "errors": errors,
        }
    
    # Data Transformation Methods
    
    def _transform_trd_buy_data(self, api_data: dict) -> dict:
        """Transform API trd_buy data to model format."""
        return {
            "goszakup_id": api_data.get("id"),
            "number": api_data.get("number"),
            "name_ru": api_data.get("name_ru"),
            "name_kz": api_data.get("name_kz"),
            "customer_bin": api_data.get("customer_bin"),
            "customer_name_ru": api_data.get("customer_name_ru"),
            "customer_name_kz": api_data.get("customer_name_kz"),
            "lots_count": api_data.get("lots_count", 0),
            "application_start_date": self._parse_datetime(api_data.get("application_start_date")),
            "application_end_date": self._parse_datetime(api_data.get("application_end_date")),
            "publish_date": self._parse_datetime(api_data.get("publish_date")),
            "purchase_type_ru": api_data.get("purchase_type_ru"),
            "purchase_type_kz": api_data.get("purchase_type_kz"),
            "status_ru": api_data.get("status_ru"),
            "status_kz": api_data.get("status_kz"),
            "total_sum": self._parse_decimal(api_data.get("total_sum")),
            "location_ru": api_data.get("location_ru"),
            "location_kz": api_data.get("location_kz"),
            "raw_data": api_data,
            "last_synced_at": datetime.utcnow(),
        }
    
    def _transform_lot_data(self, api_data: dict) -> dict:
        """Transform API lot data to model format."""
        return {
            "goszakup_id": api_data.get("id"),
            "lot_number": api_data.get("lot_number"),
            "trd_buy_id": api_data.get("trd_buy_id"),
            "description_ru": api_data.get("description_ru"),
            "description_kz": api_data.get("description_kz"),
            "ktru_code": api_data.get("ktru_code"),
            "ktru_name_ru": api_data.get("ktru_name_ru"),
            "ktru_name_kz": api_data.get("ktru_name_kz"),
            "unit_code": api_data.get("unit_code"),
            "unit_name_ru": api_data.get("unit_name_ru"),
            "unit_name_kz": api_data.get("unit_name_kz"),
            "quantity": self._parse_decimal(api_data.get("quantity")),
            "price_per_unit": self._parse_decimal(api_data.get("price_per_unit")),
            "total_sum": self._parse_decimal(api_data.get("total_sum")),
            "status_ru": api_data.get("status_ru"),
            "status_kz": api_data.get("status_kz"),
            "delivery_place_ru": api_data.get("delivery_place_ru"),
            "delivery_place_kz": api_data.get("delivery_place_kz"),
            "delivery_term": api_data.get("delivery_term"),
            "raw_data": api_data,
            "last_synced_at": datetime.utcnow(),
        }
    
    def _transform_contract_data(self, api_data: dict) -> dict:
        """Transform API contract data to model format."""
        return {
            "goszakup_id": api_data.get("id"),
            "contract_number": api_data.get("contract_number"),
            "lot_id": api_data.get("lot_id"),
            "description_ru": api_data.get("description_ru"),
            "description_kz": api_data.get("description_kz"),
            "sum": self._parse_decimal(api_data.get("sum")),
            "supplier_sum": self._parse_decimal(api_data.get("supplier_sum")),
            "customer_bin": api_data.get("customer_bin"),
            "customer_name_ru": api_data.get("customer_name_ru"),
            "customer_name_kz": api_data.get("customer_name_kz"),
            "supplier_bin": api_data.get("supplier_bin"),
            "supplier_name_ru": api_data.get("supplier_name_ru"),
            "supplier_name_kz": api_data.get("supplier_name_kz"),
            "sign_date": self._parse_datetime(api_data.get("sign_date")),
            "start_date": self._parse_datetime(api_data.get("start_date")),
            "end_date": self._parse_datetime(api_data.get("end_date")),
            "status_ru": api_data.get("status_ru"),
            "status_kz": api_data.get("status_kz"),
            "raw_data": api_data,
            "last_synced_at": datetime.utcnow(),
        }
    
    def _transform_participant_data(self, api_data: dict) -> dict:
        """Transform API participant data to model format."""
        return {
            "bin": api_data.get("bin"),
            "iin": api_data.get("iin"),
            "name_ru": api_data.get("name_ru"),
            "name_kz": api_data.get("name_kz"),
            "name_en": api_data.get("name_en"),
            "email": api_data.get("email"),
            "phone": api_data.get("phone"),
            "address_ru": api_data.get("address_ru"),
            "address_kz": api_data.get("address_kz"),
            "city_ru": api_data.get("city_ru"),
            "city_kz": api_data.get("city_kz"),
            "region_code": api_data.get("region_code"),
            "is_active": api_data.get("is_active", True),
            "participant_type": api_data.get("participant_type", "unknown"),
            "registration_date": self._parse_datetime(api_data.get("registration_date")),
            "oked_code": api_data.get("oked_code"),
            "raw_data": api_data,
            "last_synced_at": datetime.utcnow(),
        }
    
    # Utility Methods
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime from various formats."""
        if not value:
            return None
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            # Try different datetime formats
            formats = [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        
        return None
    
    def _parse_decimal(self, value: Any) -> Optional[float]:
        """Parse decimal from various formats."""
        if not value:
            return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    async def _get_last_sync_time(self, entity: str, year: int = None) -> Optional[datetime]:
        """Get last sync timestamp for entity."""
        # This would typically be stored in a sync metadata table
        # For now, we'll use the last_synced_at from the entities themselves
        
        if entity == "trd_buy":
            query = await self.session.query(func.max(TrdBuy.last_synced_at))
            if year:
                query = query.filter(TrdBuy.year == year)
        elif entity == "lots":
            query = await self.session.query(func.max(Lot.last_synced_at))
        elif entity == "contracts":
            query = await self.session.query(func.max(Contract.last_synced_at))
            if year:
                query = query.filter(Contract.year == year)
        elif entity == "participants":
            query = await self.session.query(func.max(Participant.last_synced_at))
        else:
            return None
        
        result = await self.session.execute(query)
        return result.scalar()
    
    async def _update_sync_timestamp(self, entity: str, year: int = None):
        """Update sync timestamp for entity."""
        # This would typically update a sync metadata table
        # For now, we'll just log it
        logger.info(f"Sync timestamp updated", entity=entity, year=year, timestamp=datetime.utcnow())
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        status = {
            "last_sync_times": {},
            "record_counts": {},
            "sync_health": "healthy",
        }
        
        entities = ["trd_buy", "lots", "contracts", "participants"]
        
        for entity in entities:
            try:
                last_sync = await self._get_last_sync_time(entity)
                status["last_sync_times"][entity] = last_sync.isoformat() if last_sync else None
                
                # Get record counts
                if entity == "trd_buy":
                    count = await self.trd_buy_service.count()
                elif entity == "lots":
                    count = await self.lot_service.count()
                elif entity == "contracts":
                    count = await self.contract_service.count()
                elif entity == "participants":
                    count = await self.participant_service.count()
                
                status["record_counts"][entity] = count
                
            except Exception as e:
                status["sync_health"] = "unhealthy"
                status[f"{entity}_error"] = str(e)
        
        return status 