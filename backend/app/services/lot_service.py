"""
Lot Service

Specialized service for procurement lots business logic.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lot import Lot
from app.models.trd_buy import TrdBuy
from app.models.contract import Contract
from app.services.base_service import BaseService
import structlog

logger = structlog.get_logger()


class LotService(BaseService):
    """
    Service for Lot operations.
    
    Features:
    - Advanced filtering and search by KTRU, description, etc.
    - Analytics and reporting
    - Contract status tracking
    - Price analysis
    """
    
    def __init__(self, session: AsyncSession = None):
        """Initialize Lot service."""
        super().__init__(Lot, session)
    
    # Search and Filtering
    
    async def search_lots(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Lot], int]:
        """
        Search lots by text query with advanced filtering.
        
        Args:
            query: Search query string
            filters: Additional filters
            limit: Maximum results
            offset: Results offset
            
        Returns:
            Tuple of (results, total_count)
        """
        search_fields = [
            "description_ru", "description_kz", 
            "ktru_name_ru", "ktru_name_kz",
            "unit_name_ru", "unit_name_kz"
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
            "Lot search completed",
            query=query,
            total_results=len(results),
            total_count=total_count,
        )
        
        return results, total_count
    
    async def get_by_ktru_code(
        self,
        ktru_code: str,
        year: int = None,
        include_relations: bool = False,
        limit: int = 100,
    ) -> List[Lot]:
        """
        Get lots by KTRU code.
        
        Args:
            ktru_code: KTRU classification code
            year: Year to filter by
            include_relations: Whether to include related entities
            limit: Maximum results
            
        Returns:
            List of lots with specified KTRU code
        """
        filters = {"ktru_code": ktru_code}
        if year:
            filters["year"] = year
        
        include_rels = ["trd_buy", "contracts"] if include_relations else None
        
        return await self.list(
            filters=filters,
            sort_by="created_at",
            sort_order="desc",
            limit=limit,
            include_relations=include_rels,
        )
    
    async def get_by_price_range(
        self,
        min_price: Decimal = None,
        max_price: Decimal = None,
        year: int = None,
        ktru_code: str = None,
    ) -> List[Lot]:
        """
        Get lots by price range.
        
        Args:
            min_price: Minimum price per unit
            max_price: Maximum price per unit
            year: Year to filter by
            ktru_code: KTRU code to filter by
            
        Returns:
            List of lots in price range
        """
        filters = {}
        
        if min_price is not None:
            filters["price_per_unit"] = {"gte": min_price}
        if max_price is not None:
            filters.setdefault("price_per_unit", {})["lte"] = max_price
        if year:
            filters["year"] = year
        if ktru_code:
            filters["ktru_code"] = ktru_code
        
        return await self.list(
            filters=filters,
            sort_by="price_per_unit",
            sort_order="desc",
        )
    
    async def get_lots_by_procurement(
        self,
        trd_buy_id: int,
        include_contracts: bool = False,
    ) -> List[Lot]:
        """
        Get all lots for a specific procurement.
        
        Args:
            trd_buy_id: TrdBuy ID
            include_contracts: Whether to include contract data
            
        Returns:
            List of lots for the procurement
        """
        filters = {"trd_buy_id": trd_buy_id}
        include_relations = ["contracts"] if include_contracts else None
        
        return await self.list(
            filters=filters,
            sort_by="lot_number",
            sort_order="asc",
            include_relations=include_relations,
        )
    
    # Contract Analysis
    
    async def get_lots_with_contracts(
        self,
        year: int = None,
        status: str = None,
        limit: int = 100,
    ) -> List[Lot]:
        """
        Get lots that have associated contracts.
        
        Args:
            year: Year to filter by
            status: Contract status to filter by
            limit: Maximum results
            
        Returns:
            List of lots with contracts
        """
        # This would need a custom query to check for existence of contracts
        # For now, we'll use a simple approach
        filters = {}
        if year:
            filters["year"] = year
        
        lots = await self.list(
            filters=filters,
            include_relations=["contracts"],
            limit=limit,
        )
        
        # Filter lots that have contracts
        lots_with_contracts = [
            lot for lot in lots 
            if lot.contracts and len(lot.contracts) > 0
        ]
        
        # Filter by contract status if specified
        if status:
            filtered_lots = []
            for lot in lots_with_contracts:
                matching_contracts = [
                    contract for contract in lot.contracts
                    if contract.status_ru == status
                ]
                if matching_contracts:
                    filtered_lots.append(lot)
            lots_with_contracts = filtered_lots
        
        return lots_with_contracts
    
    async def get_uncontracted_lots(
        self,
        year: int = None,
        min_value: Decimal = None,
        limit: int = 100,
    ) -> List[Lot]:
        """
        Get lots without contracts (potential failed procurements).
        
        Args:
            year: Year to filter by
            min_value: Minimum lot value
            limit: Maximum results
            
        Returns:
            List of lots without contracts
        """
        filters = {}
        if year:
            filters["year"] = year
        if min_value:
            filters["total_sum"] = {"gte": min_value}
        
        lots = await self.list(
            filters=filters,
            include_relations=["contracts"],
            limit=limit * 2,  # Get more to filter
        )
        
        # Filter lots without contracts
        uncontracted_lots = [
            lot for lot in lots 
            if not lot.contracts or len(lot.contracts) == 0
        ]
        
        return uncontracted_lots[:limit]
    
    # Analytics and Reporting
    
    async def get_lot_statistics(
        self,
        year: int = None,
        ktru_code: str = None,
        customer_bin: str = None,
    ) -> Dict[str, Any]:
        """
        Get lot statistics.
        
        Args:
            year: Year to filter by
            ktru_code: KTRU code to filter by
            customer_bin: Customer BIN to filter by
            
        Returns:
            Statistics dictionary
        """
        filters = {}
        if year:
            filters["year"] = year
        if ktru_code:
            filters["ktru_code"] = ktru_code
        if customer_bin:
            # This would need a join with trd_buy table
            pass  # For now, skip this filter
        
        # Get aggregated data
        aggregations = {
            "total_count": "count(*)",
            "total_value": "sum(total_sum)",
            "avg_value": "avg(total_sum)",
            "min_value": "min(total_sum)",
            "max_value": "max(total_sum)",
            "avg_quantity": "avg(quantity)",
            "total_quantity": "sum(quantity)",
            "avg_price_per_unit": "avg(price_per_unit)",
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
        
        # Get unit distribution
        unit_stats = await self.aggregate(
            aggregations={"count": "count(*)"},
            filters=filters,
            group_by=["unit_name_ru"],
        )
        
        stats["unit_distribution"] = {
            item["unit_name_ru"]: item["count"] 
            for item in unit_stats
        }
        
        logger.info("Lot statistics calculated", filters=filters, stats=stats)
        return stats
    
    async def get_ktru_analysis(
        self,
        year: int = None,
        top_n: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Analyze lots by KTRU codes.
        
        Args:
            year: Year to filter by
            top_n: Number of top KTRU codes to return
            
        Returns:
            List of KTRU analysis data
        """
        filters = {}
        if year:
            filters["year"] = year
        
        ktru_stats = await self.aggregate(
            aggregations={
                "lot_count": "count(*)",
                "total_value": "sum(total_sum)",
                "avg_value": "avg(total_sum)",
                "avg_quantity": "avg(quantity)",
                "avg_price_per_unit": "avg(price_per_unit)",
                "min_price": "min(price_per_unit)",
                "max_price": "max(price_per_unit)",
            },
            filters=filters,
            group_by=["ktru_code", "ktru_name_ru"],
        )
        
        # Sort by total value and return top N
        sorted_stats = sorted(
            ktru_stats,
            key=lambda x: x["total_value"] or 0,
            reverse=True,
        )
        
        return sorted_stats[:top_n]
    
    async def get_price_trends(
        self,
        ktru_code: str,
        months: int = 12,
    ) -> List[Dict[str, Any]]:
        """
        Get price trends for a specific KTRU code.
        
        Args:
            ktru_code: KTRU code to analyze
            months: Number of months to analyze
            
        Returns:
            Price trend data
        """
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=months * 30)
        
        filters = {
            "ktru_code": ktru_code,
            "created_at": {
                "gte": start_date,
                "lte": end_date,
            },
        }
        
        # Group by month and calculate price statistics
        monthly_stats = await self.aggregate(
            aggregations={
                "lot_count": "count(*)",
                "avg_price": "avg(price_per_unit)",
                "min_price": "min(price_per_unit)",
                "max_price": "max(price_per_unit)",
                "total_quantity": "sum(quantity)",
                "total_value": "sum(total_sum)",
            },
            filters=filters,
            group_by=["extract(year from created_at)", "extract(month from created_at)"],
        )
        
        return monthly_stats
    
    # Market Analysis
    
    async def get_competitive_lots(
        self,
        ktru_code: str,
        reference_price: Decimal,
        tolerance_percent: float = 10.0,
        year: int = None,
    ) -> List[Lot]:
        """
        Find lots with similar prices for market analysis.
        
        Args:
            ktru_code: KTRU code to match
            reference_price: Reference price for comparison
            tolerance_percent: Price tolerance percentage
            year: Year to filter by
            
        Returns:
            List of competitively priced lots
        """
        tolerance = reference_price * (tolerance_percent / 100)
        min_price = reference_price - tolerance
        max_price = reference_price + tolerance
        
        filters = {
            "ktru_code": ktru_code,
            "price_per_unit": {
                "gte": min_price,
                "lte": max_price,
            },
        }
        
        if year:
            filters["year"] = year
        
        return await self.list(
            filters=filters,
            sort_by="price_per_unit",
            sort_order="asc",
            include_relations=["trd_buy"],
        )
    
    async def get_market_leaders(
        self,
        ktru_code: str,
        year: int = None,
        min_lots: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get market leaders (most active participants) for a KTRU code.
        
        Args:
            ktru_code: KTRU code to analyze
            year: Year to filter by
            min_lots: Minimum number of lots to be considered a leader
            
        Returns:
            List of market leaders with statistics
        """
        filters = {"ktru_code": ktru_code}
        if year:
            filters["year"] = year
        
        # Get lots with procurement data
        lots = await self.list(
            filters=filters,
            include_relations=["trd_buy"],
        )
        
        # Group by customer
        customer_stats = {}
        for lot in lots:
            if lot.trd_buy and lot.trd_buy.customer_bin:
                customer_bin = lot.trd_buy.customer_bin
                customer_name = lot.trd_buy.customer_name_ru
                
                if customer_bin not in customer_stats:
                    customer_stats[customer_bin] = {
                        "customer_bin": customer_bin,
                        "customer_name": customer_name,
                        "lot_count": 0,
                        "total_value": 0,
                        "avg_price": 0,
                        "min_price": None,
                        "max_price": None,
                        "total_quantity": 0,
                    }
                
                stats = customer_stats[customer_bin]
                stats["lot_count"] += 1
                stats["total_value"] += lot.total_sum or 0
                stats["total_quantity"] += lot.quantity or 0
                
                if lot.price_per_unit:
                    if stats["min_price"] is None or lot.price_per_unit < stats["min_price"]:
                        stats["min_price"] = lot.price_per_unit
                    if stats["max_price"] is None or lot.price_per_unit > stats["max_price"]:
                        stats["max_price"] = lot.price_per_unit
        
        # Calculate averages and filter by minimum lots
        leaders = []
        for stats in customer_stats.values():
            if stats["lot_count"] >= min_lots:
                if stats["lot_count"] > 0:
                    stats["avg_price"] = stats["total_value"] / stats["total_quantity"] if stats["total_quantity"] > 0 else 0
                leaders.append(stats)
        
        # Sort by lot count (most active first)
        leaders.sort(key=lambda x: x["lot_count"], reverse=True)
        
        return leaders
    
    # Validation and Business Logic
    
    async def validate_lot_data(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate lot data before creation/update.
        
        Args:
            data: Lot data
            
        Returns:
            Dictionary of validation errors
        """
        errors = {}
        
        # Required fields
        required_fields = ["goszakup_id", "lot_number", "trd_buy_id"]
        for field in required_fields:
            if not data.get(field):
                errors.setdefault("required", []).append(f"{field} is required")
        
        # Numeric validation
        numeric_fields = {
            "quantity": "Quantity",
            "price_per_unit": "Price per unit",
            "total_sum": "Total sum",
        }
        
        for field, display_name in numeric_fields.items():
            if data.get(field) is not None:
                try:
                    value = float(data[field])
                    if value < 0:
                        errors.setdefault("values", []).append(f"{display_name} must be non-negative")
                except (ValueError, TypeError):
                    errors.setdefault("values", []).append(f"Invalid {display_name} format")
        
        # Consistency validation
        if data.get("quantity") and data.get("price_per_unit") and data.get("total_sum"):
            try:
                quantity = float(data["quantity"])
                price_per_unit = float(data["price_per_unit"])
                total_sum = float(data["total_sum"])
                
                expected_total = quantity * price_per_unit
                tolerance = 0.01  # 1 cent tolerance
                
                if abs(total_sum - expected_total) > tolerance:
                    errors.setdefault("consistency", []).append(
                        "Total sum does not match quantity × price per unit"
                    )
            except (ValueError, TypeError):
                pass  # Already caught in numeric validation
        
        # KTRU code validation
        if data.get("ktru_code"):
            ktru_code = data["ktru_code"]
            if not isinstance(ktru_code, str) or len(ktru_code) < 8:
                errors.setdefault("ktru", []).append("KTRU code must be at least 8 characters")
        
        return errors
    
    async def check_duplicate_lot(
        self,
        goszakup_id: int,
        lot_number: int,
        trd_buy_id: int,
        exclude_id: int = None,
    ) -> Optional[Lot]:
        """
        Check for duplicate lot.
        
        Args:
            goszakup_id: Goszakup lot ID
            lot_number: Lot number within procurement
            trd_buy_id: TrdBuy ID
            exclude_id: ID to exclude from check (for updates)
            
        Returns:
            Existing lot if found, None otherwise
        """
        filters = {
            "goszakup_id": goszakup_id,
            "lot_number": lot_number,
            "trd_buy_id": trd_buy_id,
        }
        
        if exclude_id:
            filters["id"] = {"ne": exclude_id}
        
        existing_lots = await self.list(filters=filters, limit=1)
        return existing_lots[0] if existing_lots else None
    
    # Export and Reporting
    
    async def prepare_export_data(
        self,
        filters: Dict[str, Any] = None,
        include_procurement: bool = True,
        include_contracts: bool = False,
        format_for_excel: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Prepare lot data for export.
        
        Args:
            filters: Filter criteria
            include_procurement: Whether to include procurement data
            include_contracts: Whether to include contract data
            format_for_excel: Format data for Excel compatibility
            
        Returns:
            List of formatted lot data
        """
        include_relations = []
        if include_procurement:
            include_relations.append("trd_buy")
        if include_contracts:
            include_relations.append("contracts")
        
        lots = await self.list(
            filters=filters,
            sort_by="created_at",
            sort_order="desc",
            include_relations=include_relations or None,
        )
        
        export_data = []
        
        for lot in lots:
            # Base lot data
            row = {
                "Лот ID": lot.goszakup_id,
                "Номер лота": lot.lot_number,
                "Описание": lot.description_ru,
                "КТРУ код": lot.ktru_code,
                "КТРУ наименование": lot.ktru_name_ru,
                "Количество": lot.quantity,
                "Единица измерения": lot.unit_name_ru,
                "Цена за единицу": lot.price_per_unit,
                "Общая сумма": lot.total_sum,
                "Статус": lot.status_ru,
                "Год": lot.year,
            }
            
            # Add procurement data if included
            if include_procurement and lot.trd_buy:
                row.update({
                    "Закупка ID": lot.trd_buy.goszakup_id,
                    "Номер закупки": lot.trd_buy.number,
                    "Наименование закупки": lot.trd_buy.name_ru,
                    "Заказчик БИН": lot.trd_buy.customer_bin,
                    "Заказчик": lot.trd_buy.customer_name_ru,
                    "Дата публикации": lot.trd_buy.publish_date.isoformat() if lot.trd_buy.publish_date else None,
                })
            
            # Add contract data if included
            if include_contracts and lot.contracts:
                for i, contract in enumerate(lot.contracts):
                    contract_row = row.copy()
                    contract_row.update({
                        "Договор номер": contract.contract_number,
                        "Поставщик БИН": contract.supplier_bin,
                        "Поставщик": contract.supplier_name_ru,
                        "Сумма договора": contract.sum,
                        "Дата заключения": contract.conclusion_date.isoformat() if contract.conclusion_date else None,
                        "Статус договора": contract.status_ru,
                    })
                    
                    if format_for_excel:
                        if contract_row["Сумма договора"]:
                            contract_row["Сумма договора"] = f"{contract_row['Сумма договора']:,.2f}"
                    
                    export_data.append(contract_row)
            else:
                if format_for_excel:
                    # Format numbers for Excel
                    if row["Цена за единицу"]:
                        row["Цена за единицу"] = f"{row['Цена за единицу']:,.2f}"
                    if row["Общая сумма"]:
                        row["Общая сумма"] = f"{row['Общая сумма']:,.2f}"
                    
                    # Format dates for Excel
                    if include_procurement and row.get("Дата публикации"):
                        try:
                            dt = datetime.fromisoformat(row["Дата публикации"].replace('Z', '+00:00'))
                            row["Дата публикации"] = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            pass
                
                export_data.append(row)
        
        logger.info(
            "Lot export data prepared",
            total_lots=len(lots),
            total_rows=len(export_data),
            include_procurement=include_procurement,
            include_contracts=include_contracts,
        )
        
        return export_data 