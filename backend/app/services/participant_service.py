"""
Participant Service

Specialized service for procurement participants (suppliers/customers) business logic.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.participant import Participant
from app.models.trd_buy import TrdBuy
from app.models.contract import Contract
from app.services.base_service import BaseService
import structlog

logger = structlog.get_logger()


class ParticipantService(BaseService):
    """
    Service for Participant operations.
    
    Features:
    - Participant profile management
    - Performance analytics
    - Market analysis
    - Compliance tracking
    """
    
    def __init__(self, session: AsyncSession = None):
        """Initialize Participant service."""
        super().__init__(Participant, session)
    
    # Search and Filtering
    
    async def search_participants(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Participant], int]:
        """
        Search participants by text query with advanced filtering.
        
        Args:
            query: Search query string
            filters: Additional filters
            limit: Maximum results
            offset: Results offset
            
        Returns:
            Tuple of (results, total_count)
        """
        search_fields = [
            "name_ru", "name_kz", "name_en",
            "bin", "iin",
            "address_ru", "address_kz",
            "email", "phone"
        ]
        
        # Get total count
        total_count = await self.count(filters)
        
        # Perform search
        results = await self.search(
            search_term=query,
            search_fields=search_fields,
            limit=limit,
            filters=filters,
        )
        
        logger.info(
            "Participant search completed",
            query=query,
            total_results=len(results),
            total_count=total_count,
        )
        
        return results, total_count
    
    async def get_by_bin_or_iin(
        self,
        identifier: str,
    ) -> Optional[Participant]:
        """
        Get participant by BIN or IIN.
        
        Args:
            identifier: BIN or IIN
            
        Returns:
            Participant if found, None otherwise
        """
        filters = {
            "or": [
                {"bin": identifier},
                {"iin": identifier},
            ]
        }
        
        results = await self.list(filters=filters, limit=1)
        return results[0] if results else None
    
    async def get_by_type(
        self,
        participant_type: str,
        is_active: bool = None,
        limit: int = 100,
    ) -> List[Participant]:
        """
        Get participants by type.
        
        Args:
            participant_type: Type (government, sme, individual, etc.)
            is_active: Filter by active status
            limit: Maximum results
            
        Returns:
            List of participants
        """
        filters = {"participant_type": participant_type}
        if is_active is not None:
            filters["is_active"] = is_active
        
        return await self.list(
            filters=filters,
            sort_by="name_ru",
            sort_order="asc",
            limit=limit,
        )
    
    async def get_active_participants(
        self,
        participant_type: str = None,
        region: str = None,
    ) -> List[Participant]:
        """
        Get active participants.
        
        Args:
            participant_type: Filter by participant type
            region: Filter by region
            
        Returns:
            List of active participants
        """
        filters = {"is_active": True}
        if participant_type:
            filters["participant_type"] = participant_type
        if region:
            filters["region_ru"] = region
        
        return await self.list(
            filters=filters,
            sort_by="name_ru",
            sort_order="asc",
        )
    
    async def get_blacklisted_participants(
        self,
        limit: int = 100,
    ) -> List[Participant]:
        """
        Get blacklisted participants.
        
        Args:
            limit: Maximum results
            
        Returns:
            List of blacklisted participants
        """
        filters = {"is_blacklisted": True}
        
        return await self.list(
            filters=filters,
            sort_by="blacklist_date",
            sort_order="desc",
            limit=limit,
        )
    
    # Regional Analysis
    
    async def get_by_region(
        self,
        region: str,
        participant_type: str = None,
        is_active: bool = True,
    ) -> List[Participant]:
        """
        Get participants by region.
        
        Args:
            region: Region name
            participant_type: Filter by participant type
            is_active: Filter by active status
            
        Returns:
            List of participants in region
        """
        filters = {"region_ru": region}
        if participant_type:
            filters["participant_type"] = participant_type
        if is_active is not None:
            filters["is_active"] = is_active
        
        return await self.list(
            filters=filters,
            sort_by="name_ru",
            sort_order="asc",
        )
    
    async def get_regional_statistics(
        self,
        participant_type: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Get participant statistics by region.
        
        Args:
            participant_type: Filter by participant type
            
        Returns:
            Regional statistics
        """
        filters = {}
        if participant_type:
            filters["participant_type"] = participant_type
        
        regional_stats = await self.aggregate(
            aggregations={
                "participant_count": "count(*)",
                "active_count": "sum(case when is_active then 1 else 0 end)",
                "blacklisted_count": "sum(case when is_blacklisted then 1 else 0 end)",
                "sme_count": "sum(case when is_sme then 1 else 0 end)",
            },
            filters=filters,
            group_by=["region_ru"],
        )
        
        # Calculate percentages
        for stats in regional_stats:
            total = stats["participant_count"]
            if total > 0:
                stats["active_percent"] = (stats["active_count"] / total) * 100
                stats["blacklisted_percent"] = (stats["blacklisted_count"] / total) * 100
                stats["sme_percent"] = (stats["sme_count"] / total) * 100
            else:
                stats["active_percent"] = 0
                stats["blacklisted_percent"] = 0
                stats["sme_percent"] = 0
        
        return sorted(regional_stats, key=lambda x: x["participant_count"], reverse=True)
    
    # Performance Analysis
    
    async def analyze_participant_activity(
        self,
        bin_or_iin: str,
        include_details: bool = False,
    ) -> Dict[str, Any]:
        """
        Analyze participant activity across procurements and contracts.
        
        Args:
            bin_or_iin: Participant BIN or IIN
            include_details: Whether to include detailed records
            
        Returns:
            Activity analysis
        """
        participant = await self.get_by_bin_or_iin(bin_or_iin)
        if not participant:
            return {"error": "Participant not found"}
        
        # Get related data (this would need proper relationships)
        # For now, we'll return participant information with placeholders
        analysis = {
            "participant": {
                "bin": participant.bin,
                "iin": participant.iin,
                "name": participant.display_name,
                "type": participant.participant_type,
                "status": participant.status_display,
                "region": participant.region_ru,
                "is_active": participant.is_active,
                "is_blacklisted": participant.is_blacklisted,
            },
            "activity_summary": {
                "as_customer": {
                    "procurement_count": 0,
                    "total_value": 0,
                    "years_active": [],
                },
                "as_supplier": {
                    "contract_count": 0,
                    "total_value": 0,
                    "years_active": [],
                },
            },
            "performance_metrics": {
                "success_rate": 0,
                "avg_contract_value": 0,
                "completion_rate": 0,
            },
        }
        
        # TODO: Add actual queries for related data when relationships are established
        # This would require joins with TrdBuy and Contract tables
        
        logger.info("Participant activity analysis completed", identifier=bin_or_iin)
        return analysis
    
    async def get_top_customers(
        self,
        limit: int = 10,
        year: int = None,
        region: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Get top customers by procurement activity.
        
        Args:
            limit: Number of top customers to return
            year: Year to filter by
            region: Region to filter by
            
        Returns:
            List of top customers
        """
        filters = {"participant_type": "government"}  # Assuming customers are government entities
        if region:
            filters["region_ru"] = region
        
        # Get participants who are likely to be customers
        customers = await self.list(
            filters=filters,
            sort_by="name_ru",
            sort_order="asc",
            limit=limit * 2,  # Get more to analyze
        )
        
        # TODO: Add actual procurement volume analysis
        # This would require joining with TrdBuy table to get procurement statistics
        
        top_customers = []
        for customer in customers[:limit]:
            customer_data = {
                "bin": customer.bin,
                "name": customer.display_name,
                "region": customer.region_ru,
                "type": customer.participant_type,
                "procurement_count": 0,  # TODO: Calculate from TrdBuy
                "total_value": 0,  # TODO: Calculate from TrdBuy
                "avg_value": 0,  # TODO: Calculate from TrdBuy
            }
            top_customers.append(customer_data)
        
        return top_customers
    
    async def get_top_suppliers(
        self,
        limit: int = 10,
        year: int = None,
        region: str = None,
        min_contracts: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Get top suppliers by contract activity.
        
        Args:
            limit: Number of top suppliers to return
            year: Year to filter by
            region: Region to filter by
            min_contracts: Minimum number of contracts
            
        Returns:
            List of top suppliers
        """
        filters = {"is_active": True}
        if region:
            filters["region_ru"] = region
        
        # Get active participants who could be suppliers
        suppliers = await self.list(
            filters=filters,
            sort_by="name_ru",
            sort_order="asc",
            limit=limit * 2,  # Get more to analyze
        )
        
        # TODO: Add actual contract volume analysis
        # This would require joining with Contract table to get contract statistics
        
        top_suppliers = []
        for supplier in suppliers[:limit]:
            supplier_data = {
                "bin": supplier.bin,
                "iin": supplier.iin,
                "name": supplier.display_name,
                "region": supplier.region_ru,
                "type": supplier.participant_type,
                "is_sme": supplier.is_sme,
                "contract_count": 0,  # TODO: Calculate from Contract
                "total_value": 0,  # TODO: Calculate from Contract
                "avg_value": 0,  # TODO: Calculate from Contract
                "success_rate": 0,  # TODO: Calculate completion rate
            }
            top_suppliers.append(supplier_data)
        
        return top_suppliers
    
    # Compliance and Verification
    
    async def get_compliance_status(
        self,
        bin_or_iin: str,
    ) -> Dict[str, Any]:
        """
        Get participant compliance status.
        
        Args:
            bin_or_iin: Participant BIN or IIN
            
        Returns:
            Compliance status information
        """
        participant = await self.get_by_bin_or_iin(bin_or_iin)
        if not participant:
            return {"error": "Participant not found"}
        
        compliance = {
            "participant_id": participant.id,
            "identifier": participant.bin or participant.iin,
            "name": participant.display_name,
            "status": {
                "is_active": participant.is_active,
                "is_blacklisted": participant.is_blacklisted,
                "blacklist_reason": participant.blacklist_reason,
                "blacklist_date": participant.blacklist_date.isoformat() if participant.blacklist_date else None,
            },
            "registration": {
                "registration_date": participant.registration_date.isoformat() if participant.registration_date else None,
                "last_update": participant.last_update_date.isoformat() if participant.last_update_date else None,
            },
            "verification": {
                "data_source": "goszakup_api",
                "last_sync": participant.last_sync_date.isoformat() if participant.last_sync_date else None,
                "verification_status": "verified" if participant.is_active else "needs_verification",
            },
        }
        
        return compliance
    
    async def verify_participant_data(
        self,
        bin_or_iin: str,
    ) -> Dict[str, Any]:
        """
        Verify participant data completeness and consistency.
        
        Args:
            bin_or_iin: Participant BIN or IIN
            
        Returns:
            Verification results
        """
        participant = await self.get_by_bin_or_iin(bin_or_iin)
        if not participant:
            return {"error": "Participant not found"}
        
        verification = {
            "participant_id": participant.id,
            "identifier": participant.bin or participant.iin,
            "completeness": {
                "score": 0,
                "total_fields": 0,
                "complete_fields": 0,
                "missing_fields": [],
            },
            "consistency": {
                "score": 100,  # Start with perfect score
                "issues": [],
            },
            "data_quality": {
                "score": 0,
                "issues": [],
            },
        }
        
        # Check data completeness
        required_fields = [
            ("bin", "БИН"),
            ("name_ru", "Наименование на русском"),
            ("participant_type", "Тип участника"),
            ("region_ru", "Регион"),
        ]
        
        optional_fields = [
            ("name_kz", "Наименование на казахском"),
            ("name_en", "Наименование на английском"),
            ("address_ru", "Адрес на русском"),
            ("email", "Email"),
            ("phone", "Телефон"),
            ("website", "Веб-сайт"),
        ]
        
        all_fields = required_fields + optional_fields
        verification["completeness"]["total_fields"] = len(all_fields)
        
        for field, field_name in all_fields:
            value = getattr(participant, field, None)
            if value:
                verification["completeness"]["complete_fields"] += 1
            else:
                verification["completeness"]["missing_fields"].append(field_name)
        
        verification["completeness"]["score"] = (
            verification["completeness"]["complete_fields"] / 
            verification["completeness"]["total_fields"]
        ) * 100
        
        # Check data consistency
        if participant.bin and len(participant.bin) != 12:
            verification["consistency"]["issues"].append("БИН должен содержать 12 цифр")
            verification["consistency"]["score"] -= 20
        
        if participant.iin and len(participant.iin) != 12:
            verification["consistency"]["issues"].append("ИИН должен содержать 12 цифр")
            verification["consistency"]["score"] -= 20
        
        if participant.email and "@" not in participant.email:
            verification["consistency"]["issues"].append("Некорректный формат email")
            verification["consistency"]["score"] -= 10
        
        # Calculate overall data quality score
        verification["data_quality"]["score"] = (
            verification["completeness"]["score"] * 0.6 +
            verification["consistency"]["score"] * 0.4
        )
        
        if verification["data_quality"]["score"] < 70:
            verification["data_quality"]["issues"].append("Низкое качество данных")
        
        return verification
    
    # Statistics and Analytics
    
    async def get_participant_statistics(
        self,
        participant_type: str = None,
        region: str = None,
    ) -> Dict[str, Any]:
        """
        Get participant statistics.
        
        Args:
            participant_type: Filter by participant type
            region: Filter by region
            
        Returns:
            Statistics dictionary
        """
        filters = {}
        if participant_type:
            filters["participant_type"] = participant_type
        if region:
            filters["region_ru"] = region
        
        # Get aggregated data
        aggregations = {
            "total_count": "count(*)",
            "active_count": "sum(case when is_active then 1 else 0 end)",
            "blacklisted_count": "sum(case when is_blacklisted then 1 else 0 end)",
            "sme_count": "sum(case when is_sme then 1 else 0 end)",
            "individual_count": "sum(case when participant_type = 'individual' then 1 else 0 end)",
            "government_count": "sum(case when participant_type = 'government' then 1 else 0 end)",
        }
        
        results = await self.aggregate(
            aggregations=aggregations,
            filters=filters,
        )
        
        stats = results[0] if results else {}
        
        # Calculate percentages
        total = stats.get("total_count", 0)
        if total > 0:
            stats["active_percent"] = (stats.get("active_count", 0) / total) * 100
            stats["blacklisted_percent"] = (stats.get("blacklisted_count", 0) / total) * 100
            stats["sme_percent"] = (stats.get("sme_count", 0) / total) * 100
        else:
            stats["active_percent"] = 0
            stats["blacklisted_percent"] = 0
            stats["sme_percent"] = 0
        
        # Get type distribution
        type_stats = await self.aggregate(
            aggregations={"count": "count(*)"},
            filters=filters,
            group_by=["participant_type"],
        )
        
        stats["type_distribution"] = {
            item["participant_type"]: item["count"] 
            for item in type_stats
        }
        
        logger.info("Participant statistics calculated", filters=filters, stats=stats)
        return stats
    
    # Validation and Business Logic
    
    async def validate_participant_data(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate participant data before creation/update.
        
        Args:
            data: Participant data
            
        Returns:
            Dictionary of validation errors
        """
        errors = {}
        
        # Either BIN or IIN is required
        if not data.get("bin") and not data.get("iin"):
            errors.setdefault("required", []).append("Either BIN or IIN is required")
        
        # BIN validation
        if data.get("bin"):
            bin_value = str(data["bin"])
            if not bin_value.isdigit() or len(bin_value) != 12:
                errors.setdefault("format", []).append("BIN must be 12 digits")
        
        # IIN validation
        if data.get("iin"):
            iin_value = str(data["iin"])
            if not iin_value.isdigit() or len(iin_value) != 12:
                errors.setdefault("format", []).append("IIN must be 12 digits")
        
        # Required fields
        required_fields = ["name_ru", "participant_type"]
        for field in required_fields:
            if not data.get(field):
                errors.setdefault("required", []).append(f"{field} is required")
        
        # Email validation
        if data.get("email"):
            email = data["email"]
            if "@" not in email or "." not in email:
                errors.setdefault("format", []).append("Invalid email format")
        
        # Participant type validation
        if data.get("participant_type"):
            valid_types = ["government", "individual", "legal_entity", "foreign", "sme"]
            if data["participant_type"] not in valid_types:
                errors.setdefault("values", []).append(f"Invalid participant type. Must be one of: {valid_types}")
        
        return errors
    
    async def check_duplicate_participant(
        self,
        bin_value: str = None,
        iin_value: str = None,
        exclude_id: int = None,
    ) -> Optional[Participant]:
        """
        Check for duplicate participant by BIN or IIN.
        
        Args:
            bin_value: BIN to check
            iin_value: IIN to check
            exclude_id: ID to exclude from check (for updates)
            
        Returns:
            Existing participant if found, None otherwise
        """
        if not bin_value and not iin_value:
            return None
        
        filters = {"or": []}
        if bin_value:
            filters["or"].append({"bin": bin_value})
        if iin_value:
            filters["or"].append({"iin": iin_value})
        
        if exclude_id:
            filters["id"] = {"ne": exclude_id}
        
        existing_participants = await self.list(filters=filters, limit=1)
        return existing_participants[0] if existing_participants else None
    
    # Export and Reporting
    
    async def prepare_export_data(
        self,
        filters: Dict[str, Any] = None,
        format_for_excel: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Prepare participant data for export.
        
        Args:
            filters: Filter criteria
            format_for_excel: Format data for Excel compatibility
            
        Returns:
            List of formatted participant data
        """
        participants = await self.list(
            filters=filters,
            sort_by="name_ru",
            sort_order="asc",
        )
        
        export_data = []
        
        for participant in participants:
            # Base participant data
            row = {
                "БИН": participant.bin,
                "ИИН": participant.iin,
                "Наименование": participant.name_ru,
                "Наименование (каз)": participant.name_kz,
                "Наименование (англ)": participant.name_en,
                "Тип участника": participant.participant_type,
                "Статус": "Активный" if participant.is_active else "Неактивный",
                "В черном списке": "Да" if participant.is_blacklisted else "Нет",
                "МСБ": "Да" if participant.is_sme else "Нет",
                "Регион": participant.region_ru,
                "Адрес": participant.address_ru,
                "Email": participant.email,
                "Телефон": participant.phone,
                "Веб-сайт": participant.website,
                "Дата регистрации": participant.registration_date.isoformat() if participant.registration_date else None,
                "Последнее обновление": participant.last_update_date.isoformat() if participant.last_update_date else None,
            }
            
            if format_for_excel:
                # Format dates for Excel
                date_fields = ["Дата регистрации", "Последнее обновление"]
                for field in date_fields:
                    if row[field]:
                        try:
                            dt = datetime.fromisoformat(row[field])
                            row[field] = dt.strftime("%Y-%m-%d")
                        except:
                            pass
            
            export_data.append(row)
        
        logger.info(
            "Participant export data prepared",
            total_participants=len(participants),
            total_rows=len(export_data),
        )
        
        return export_data 