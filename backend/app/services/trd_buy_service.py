"""
TrdBuy Service

Specialized service for procurement announcements (trd_buy) business logic.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.trd_buy import TrdBuy
from app.models.lot import Lot
from app.models.participant import Participant
from app.services.base_service import BaseService
import structlog

logger = structlog.get_logger()


class TrdBuyService(BaseService):
    """
    Service for TrdBuy (procurement announcements) operations.
    
    Features:
    - Advanced filtering and search
    - Analytics and reporting
    - Status tracking
    - Customer analysis
    """
    
    def __init__(self, session: AsyncSession = None):
        """Initialize TrdBuy service."""
        super().__init__(TrdBuy, session)
    
    # Search and Filtering
    
    async def search_procurements(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[TrdBuy], int]:
        """
        Search procurements by text query with advanced filtering.
        
        Args:
            query: Search query string
            filters: Additional filters
            limit: Maximum results
            offset: Results offset
            
        Returns:
            Tuple of (results, total_count)
        """
        search_fields = ["name_ru", "name_kz", "customer_name_ru", "customer_name_kz"]
        
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
            "Procurement search completed",
            query=query,
            total_results=len(results),
            total_count=total_count,
        )
        
        return results, total_count
    
    async def filter_by_date_range(
        self,
        start_date: date,
        end_date: date,
        date_field: str = "publish_date",
        additional_filters: Dict[str, Any] = None,
    ) -> List[TrdBuy]:
        """
        Filter procurements by date range.
        
        Args:
            start_date: Start date
            end_date: End date
            date_field: Date field to filter by
            additional_filters: Additional filter criteria
            
        Returns:
            List of filtered procurements
        """
        filters = additional_filters or {}
        filters[date_field] = {
            "gte": start_date,
            "lte": end_date,
        }
        
        return await self.list(
            filters=filters,
            sort_by=date_field,
            sort_order="desc",
        )
    
    async def get_active_procurements(
        self,
        include_lots: bool = False,
    ) -> List[TrdBuy]:
        """
        Get currently active procurements.
        
        Args:
            include_lots: Whether to include related lots
            
        Returns:
            List of active procurements
        """
        now = datetime.utcnow()
        filters = {
            "application_start_date": {"lte": now},
            "application_end_date": {"gte": now},
        }
        
        include_relations = ["lots"] if include_lots else None
        
        return await self.list(
            filters=filters,
            sort_by="application_end_date",
            sort_order="asc",
            include_relations=include_relations,
        )
    
    async def get_expiring_soon(
        self,
        days: int = 7,
        include_lots: bool = False,
    ) -> List[TrdBuy]:
        """
        Get procurements expiring within specified days.
        
        Args:
            days: Number of days ahead to check
            include_lots: Whether to include related lots
            
        Returns:
            List of expiring procurements
        """
        now = datetime.utcnow()
        expiry_date = now + timedelta(days=days)
        
        filters = {
            "application_end_date": {
                "gte": now,
                "lte": expiry_date,
            },
        }
        
        include_relations = ["lots"] if include_lots else None
        
        return await self.list(
            filters=filters,
            sort_by="application_end_date",
            sort_order="asc",
            include_relations=include_relations,
        )
    
    # Analytics and Reporting
    
    async def get_procurement_stats(
        self,
        year: int = None,
        customer_bin: str = None,
    ) -> Dict[str, Any]:
        """
        Get procurement statistics.
        
        Args:
            year: Year to filter by
            customer_bin: Customer BIN to filter by
            
        Returns:
            Statistics dictionary
        """
        filters = {}
        if year:
            filters["year"] = year
        if customer_bin:
            filters["customer_bin"] = customer_bin
        
        # Get aggregated data
        aggregations = {
            "total_count": "count(*)",
            "total_sum": "sum(total_sum)",
            "avg_sum": "avg(total_sum)",
            "min_sum": "min(total_sum)",
            "max_sum": "max(total_sum)",
            "total_lots": "sum(lots_count)",
        }
        
        results = await self.aggregate(
            aggregations=aggregations,
            filters=filters,
        )
        
        stats = results[0] if results else {}
        
        # Get status distribution
        status_stats = await self.aggregate(
            aggregations={"count": "count(*)"},
            filters=filters,
            group_by=["status_ru"],
        )
        
        stats["status_distribution"] = {
            item["status_ru"]: item["count"] 
            for item in status_stats
        }
        
        # Get monthly distribution if year is specified
        if year:
            monthly_stats = await self.aggregate(
                aggregations={
                    "count": "count(*)",
                    "total_sum": "sum(total_sum)",
                },
                filters=filters,
                group_by=["extract(month from publish_date)"],
            )
            
            stats["monthly_distribution"] = {
                int(item["extract"]): {
                    "count": item["count"],
                    "total_sum": item["total_sum"],
                }
                for item in monthly_stats
            }
        
        logger.info("Procurement stats calculated", filters=filters, stats=stats)
        return stats
    
    async def get_top_customers(
        self,
        limit: int = 10,
        year: int = None,
        min_procurements: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Get top customers by procurement volume.
        
        Args:
            limit: Number of top customers to return
            year: Year to filter by
            min_procurements: Minimum number of procurements
            
        Returns:
            List of top customers with statistics
        """
        filters = {}
        if year:
            filters["year"] = year
        
        customer_stats = await self.aggregate(
            aggregations={
                "procurement_count": "count(*)",
                "total_sum": "sum(total_sum)",
                "avg_sum": "avg(total_sum)",
                "total_lots": "sum(lots_count)",
            },
            filters=filters,
            group_by=["customer_bin", "customer_name_ru"],
        )
        
        # Filter by minimum procurements and sort
        filtered_stats = [
            stats for stats in customer_stats
            if stats["procurement_count"] >= min_procurements
        ]
        
        sorted_stats = sorted(
            filtered_stats,
            key=lambda x: x["total_sum"] or 0,
            reverse=True,
        )
        
        return sorted_stats[:limit]
    
    async def get_procurement_timeline(
        self,
        customer_bin: str = None,
        year: int = None,
        group_by: str = "month",
    ) -> List[Dict[str, Any]]:
        """
        Get procurement timeline data.
        
        Args:
            customer_bin: Customer BIN to filter by
            year: Year to filter by
            group_by: Grouping period (month, quarter, year)
            
        Returns:
            Timeline data
        """
        filters = {}
        if customer_bin:
            filters["customer_bin"] = customer_bin
        if year:
            filters["year"] = year
        
        # Define grouping expression
        if group_by == "month":
            group_expr = "extract(year from publish_date), extract(month from publish_date)"
            group_fields = ["extract(year from publish_date)", "extract(month from publish_date)"]
        elif group_by == "quarter":
            group_expr = "extract(year from publish_date), extract(quarter from publish_date)"
            group_fields = ["extract(year from publish_date)", "extract(quarter from publish_date)"]
        else:  # year
            group_expr = "extract(year from publish_date)"
            group_fields = ["extract(year from publish_date)"]
        
        timeline_data = await self.aggregate(
            aggregations={
                "count": "count(*)",
                "total_sum": "sum(total_sum)",
                "avg_sum": "avg(total_sum)",
                "lots_count": "sum(lots_count)",
            },
            filters=filters,
            group_by=group_fields,
        )
        
        return timeline_data
    
    # Customer Analysis
    
    async def get_customer_procurements(
        self,
        customer_bin: str,
        year: int = None,
        include_lots: bool = False,
        sort_by: str = "publish_date",
        sort_order: str = "desc",
    ) -> List[TrdBuy]:
        """
        Get all procurements for a specific customer.
        
        Args:
            customer_bin: Customer BIN
            year: Year to filter by
            include_lots: Whether to include related lots
            sort_by: Field to sort by
            sort_order: Sort order
            
        Returns:
            List of customer procurements
        """
        filters = {"customer_bin": customer_bin}
        if year:
            filters["year"] = year
        
        include_relations = ["lots"] if include_lots else None
        
        return await self.list(
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            include_relations=include_relations,
        )
    
    async def analyze_customer_behavior(
        self,
        customer_bin: str,
    ) -> Dict[str, Any]:
        """
        Analyze customer procurement behavior patterns.
        
        Args:
            customer_bin: Customer BIN
            
        Returns:
            Customer behavior analysis
        """
        # Get customer procurements
        procurements = await self.get_customer_procurements(customer_bin)
        
        if not procurements:
            return {"error": "No procurements found for customer"}
        
        analysis = {
            "customer_bin": customer_bin,
            "customer_name": procurements[0].customer_name_ru,
            "total_procurements": len(procurements),
            "years_active": [],
            "avg_procurement_value": 0,
            "total_value": 0,
            "procurement_frequency": {},
            "status_distribution": {},
            "purchase_type_distribution": {},
        }
        
        # Calculate statistics
        total_sum = sum(p.total_sum or 0 for p in procurements)
        analysis["total_value"] = total_sum
        analysis["avg_procurement_value"] = total_sum / len(procurements)
        
        # Years active
        years = set(p.year for p in procurements if p.year)
        analysis["years_active"] = sorted(years)
        
        # Frequency analysis (procurements per year)
        year_counts = {}
        for procurement in procurements:
            year = procurement.year
            if year:
                year_counts[year] = year_counts.get(year, 0) + 1
        analysis["procurement_frequency"] = year_counts
        
        # Status distribution
        status_counts = {}
        for procurement in procurements:
            status = procurement.status_ru or "Unknown"
            status_counts[status] = status_counts.get(status, 0) + 1
        analysis["status_distribution"] = status_counts
        
        # Purchase type distribution
        type_counts = {}
        for procurement in procurements:
            ptype = procurement.purchase_type_ru or "Unknown"
            type_counts[ptype] = type_counts.get(ptype, 0) + 1
        analysis["purchase_type_distribution"] = type_counts
        
        logger.info("Customer behavior analysis completed", customer_bin=customer_bin)
        return analysis
    
    # Specialized Queries
    
    async def get_large_procurements(
        self,
        min_sum: float,
        year: int = None,
        limit: int = 100,
    ) -> List[TrdBuy]:
        """
        Get procurements above a certain value threshold.
        
        Args:
            min_sum: Minimum procurement sum
            year: Year to filter by
            limit: Maximum results
            
        Returns:
            List of large procurements
        """
        filters = {"total_sum": {"gte": min_sum}}
        if year:
            filters["year"] = year
        
        return await self.list(
            filters=filters,
            sort_by="total_sum",
            sort_order="desc",
            limit=limit,
        )
    
    async def get_multi_lot_procurements(
        self,
        min_lots: int = 2,
        year: int = None,
        include_lots: bool = True,
    ) -> List[TrdBuy]:
        """
        Get procurements with multiple lots.
        
        Args:
            min_lots: Minimum number of lots
            year: Year to filter by
            include_lots: Whether to include related lots
            
        Returns:
            List of multi-lot procurements
        """
        filters = {"lots_count": {"gte": min_lots}}
        if year:
            filters["year"] = year
        
        include_relations = ["lots"] if include_lots else None
        
        return await self.list(
            filters=filters,
            sort_by="lots_count",
            sort_order="desc",
            include_relations=include_relations,
        )
    
    async def get_by_location(
        self,
        location_query: str,
        year: int = None,
        limit: int = 100,
    ) -> List[TrdBuy]:
        """
        Get procurements by location.
        
        Args:
            location_query: Location search query
            year: Year to filter by
            limit: Maximum results
            
        Returns:
            List of procurements in location
        """
        filters = {}
        if year:
            filters["year"] = year
        
        # Use search across location fields
        location_fields = ["location_ru", "location_kz"]
        
        return await self.search(
            search_term=location_query,
            search_fields=location_fields,
            limit=limit,
            filters=filters,
        )
    
    # Validation and Business Logic
    
    async def validate_procurement_data(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate procurement data before creation/update.
        
        Args:
            data: Procurement data
            
        Returns:
            Dictionary of validation errors
        """
        errors = {}
        
        # Required fields
        required_fields = ["goszakup_id", "number", "name_ru", "customer_bin"]
        for field in required_fields:
            if not data.get(field):
                errors.setdefault("required", []).append(f"{field} is required")
        
        # Date validation
        if data.get("application_start_date") and data.get("application_end_date"):
            start_date = data["application_start_date"]
            end_date = data["application_end_date"]
            
            if isinstance(start_date, str):
                try:
                    start_date = datetime.fromisoformat(start_date)
                except ValueError:
                    errors.setdefault("dates", []).append("Invalid application_start_date format")
            
            if isinstance(end_date, str):
                try:
                    end_date = datetime.fromisoformat(end_date)
                except ValueError:
                    errors.setdefault("dates", []).append("Invalid application_end_date format")
            
            if isinstance(start_date, datetime) and isinstance(end_date, datetime):
                if start_date >= end_date:
                    errors.setdefault("dates", []).append(
                        "application_start_date must be before application_end_date"
                    )
        
        # Value validation
        if data.get("total_sum") is not None:
            try:
                total_sum = float(data["total_sum"])
                if total_sum < 0:
                    errors.setdefault("values", []).append("total_sum must be non-negative")
            except (ValueError, TypeError):
                errors.setdefault("values", []).append("Invalid total_sum format")
        
        # Lots count validation
        if data.get("lots_count") is not None:
            try:
                lots_count = int(data["lots_count"])
                if lots_count < 0:
                    errors.setdefault("values", []).append("lots_count must be non-negative")
            except (ValueError, TypeError):
                errors.setdefault("values", []).append("Invalid lots_count format")
        
        return errors
    
    async def check_duplicate_procurement(
        self,
        goszakup_id: int,
        number: str,
        exclude_id: int = None,
    ) -> Optional[TrdBuy]:
        """
        Check for duplicate procurement by Goszakup ID or number.
        
        Args:
            goszakup_id: Goszakup procurement ID
            number: Procurement number
            exclude_id: ID to exclude from check (for updates)
            
        Returns:
            Existing procurement if found, None otherwise
        """
        session = await self.session
        
        query = session.query(self.model).filter(
            or_(
                self.model.goszakup_id == goszakup_id,
                self.model.number == number,
            )
        )
        
        if exclude_id:
            query = query.filter(self.model.id != exclude_id)
        
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    # Export and Reporting
    
    async def prepare_export_data(
        self,
        filters: Dict[str, Any] = None,
        include_lots: bool = False,
        format_for_excel: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Prepare procurement data for export.
        
        Args:
            filters: Filter criteria
            include_lots: Whether to include lot data
            format_for_excel: Format data for Excel compatibility
            
        Returns:
            List of formatted procurement data
        """
        include_relations = ["lots"] if include_lots else None
        
        procurements = await self.list(
            filters=filters,
            sort_by="publish_date",
            sort_order="desc",
            include_relations=include_relations,
        )
        
        export_data = []
        
        for procurement in procurements:
            # Base procurement data
            row = {
                "ID": procurement.goszakup_id,
                "Номер": procurement.number,
                "Наименование": procurement.name_ru,
                "Заказчик БИН": procurement.customer_bin,
                "Заказчик": procurement.customer_name_ru,
                "Количество лотов": procurement.lots_count,
                "Общая сумма": procurement.total_sum,
                "Дата публикации": procurement.publish_date.isoformat() if procurement.publish_date else None,
                "Начало подач": procurement.application_start_date.isoformat() if procurement.application_start_date else None,
                "Окончание подач": procurement.application_end_date.isoformat() if procurement.application_end_date else None,
                "Тип закупки": procurement.purchase_type_ru,
                "Статус": procurement.status_ru,
                "Местоположение": procurement.location_ru,
                "Год": procurement.year,
            }
            
            if format_for_excel:
                # Format dates for Excel
                for field in ["Дата публикации", "Начало подач", "Окончание подач"]:
                    if row[field]:
                        try:
                            dt = datetime.fromisoformat(row[field].replace('Z', '+00:00'))
                            row[field] = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            pass
                
                # Format numbers for Excel
                if row["Общая сумма"]:
                    row["Общая сумма"] = f"{row['Общая сумма']:,.2f}"
            
            # Add lot data if included
            if include_lots and procurement.lots:
                for i, lot in enumerate(procurement.lots):
                    lot_row = row.copy()
                    lot_row.update({
                        "Лот номер": lot.lot_number,
                        "Описание лота": lot.description_ru,
                        "КТРУ код": lot.ktru_code,
                        "КТРУ наименование": lot.ktru_name_ru,
                        "Количество": lot.quantity,
                        "Цена за единицу": lot.price_per_unit,
                        "Сумма лота": lot.total_sum,
                        "Единица измерения": lot.unit_name_ru,
                        "Статус лота": lot.status_ru,
                    })
                    
                    if format_for_excel and lot_row["Сумма лота"]:
                        lot_row["Сумма лота"] = f"{lot_row['Сумма лота']:,.2f}"
                    
                    export_data.append(lot_row)
            else:
                export_data.append(row)
        
        logger.info(
            "Export data prepared",
            total_procurements=len(procurements),
            total_rows=len(export_data),
            include_lots=include_lots,
        )
        
        return export_data 