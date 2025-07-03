"""
Contract Service

Specialized service for procurement contracts business logic.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.contract import Contract
from app.models.lot import Lot
from app.models.trd_buy import TrdBuy
from app.models.participant import Participant
from app.services.base_service import BaseService
import structlog

logger = structlog.get_logger()


class ContractService(BaseService):
    """
    Service for Contract operations.
    
    Features:
    - Contract lifecycle tracking
    - Supplier performance analysis
    - Financial analytics
    - Compliance monitoring
    """
    
    def __init__(self, session: AsyncSession = None):
        """Initialize Contract service."""
        super().__init__(Contract, session)
    
    # Search and Filtering
    
    async def search_contracts(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Contract], int]:
        """
        Search contracts by text query with advanced filtering.
        
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
            "contract_number",
            "customer_name_ru", "customer_name_kz",
            "supplier_name_ru", "supplier_name_kz"
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
            "Contract search completed",
            query=query,
            total_results=len(results),
            total_count=total_count,
        )
        
        return results, total_count
    
    async def get_by_date_range(
        self,
        start_date: date,
        end_date: date,
        date_field: str = "conclusion_date",
        additional_filters: Dict[str, Any] = None,
    ) -> List[Contract]:
        """
        Filter contracts by date range.
        
        Args:
            start_date: Start date
            end_date: End date
            date_field: Date field to filter by
            additional_filters: Additional filter criteria
            
        Returns:
            List of filtered contracts
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
    
    async def get_active_contracts(
        self,
        include_relations: bool = False,
    ) -> List[Contract]:
        """
        Get currently active contracts.
        
        Args:
            include_relations: Whether to include related entities
            
        Returns:
            List of active contracts
        """
        now = datetime.utcnow().date()
        filters = {
            "execution_start_date": {"lte": now},
            "execution_end_date": {"gte": now},
        }
        
        include_rels = ["lot", "lot.trd_buy"] if include_relations else None
        
        return await self.list(
            filters=filters,
            sort_by="execution_end_date",
            sort_order="asc",
            include_relations=include_rels,
        )
    
    async def get_expiring_contracts(
        self,
        days: int = 30,
        include_relations: bool = False,
    ) -> List[Contract]:
        """
        Get contracts expiring within specified days.
        
        Args:
            days: Number of days ahead to check
            include_relations: Whether to include related entities
            
        Returns:
            List of expiring contracts
        """
        now = datetime.utcnow().date()
        expiry_date = now + timedelta(days=days)
        
        filters = {
            "execution_end_date": {
                "gte": now,
                "lte": expiry_date,
            },
        }
        
        include_rels = ["lot", "lot.trd_buy"] if include_relations else None
        
        return await self.list(
            filters=filters,
            sort_by="execution_end_date",
            sort_order="asc",
            include_relations=include_rels,
        )
    
    # Supplier Analysis
    
    async def get_supplier_contracts(
        self,
        supplier_bin: str,
        year: int = None,
        include_relations: bool = False,
        sort_by: str = "conclusion_date",
        sort_order: str = "desc",
    ) -> List[Contract]:
        """
        Get all contracts for a specific supplier.
        
        Args:
            supplier_bin: Supplier BIN
            year: Year to filter by
            include_relations: Whether to include related entities
            sort_by: Field to sort by
            sort_order: Sort order
            
        Returns:
            List of supplier contracts
        """
        filters = {"supplier_bin": supplier_bin}
        if year:
            filters["year"] = year
        
        include_rels = ["lot", "lot.trd_buy"] if include_relations else None
        
        return await self.list(
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            include_relations=include_rels,
        )
    
    async def analyze_supplier_performance(
        self,
        supplier_bin: str,
    ) -> Dict[str, Any]:
        """
        Analyze supplier performance across all contracts.
        
        Args:
            supplier_bin: Supplier BIN
            
        Returns:
            Supplier performance analysis
        """
        # Get supplier contracts
        contracts = await self.get_supplier_contracts(supplier_bin, include_relations=True)
        
        if not contracts:
            return {"error": "No contracts found for supplier"}
        
        analysis = {
            "supplier_bin": supplier_bin,
            "supplier_name": contracts[0].supplier_name_ru,
            "total_contracts": len(contracts),
            "years_active": [],
            "total_value": 0,
            "avg_contract_value": 0,
            "contract_frequency": {},
            "status_distribution": {},
            "customer_distribution": {},
            "execution_performance": {
                "on_time": 0,
                "delayed": 0,
                "terminated": 0,
                "active": 0,
            },
        }
        
        # Calculate statistics
        total_value = sum(c.sum or 0 for c in contracts)
        analysis["total_value"] = total_value
        analysis["avg_contract_value"] = total_value / len(contracts)
        
        # Years active
        years = set(c.year for c in contracts if c.year)
        analysis["years_active"] = sorted(years)
        
        # Frequency analysis (contracts per year)
        year_counts = {}
        for contract in contracts:
            year = contract.year
            if year:
                year_counts[year] = year_counts.get(year, 0) + 1
        analysis["contract_frequency"] = year_counts
        
        # Status distribution
        status_counts = {}
        for contract in contracts:
            status = contract.status_ru or "Unknown"
            status_counts[status] = status_counts.get(status, 0) + 1
        analysis["status_distribution"] = status_counts
        
        # Customer distribution
        customer_counts = {}
        for contract in contracts:
            customer = contract.customer_name_ru or "Unknown"
            customer_counts[customer] = customer_counts.get(customer, 0) + 1
        analysis["customer_distribution"] = customer_counts
        
        # Execution performance
        now = datetime.utcnow().date()
        for contract in contracts:
            if contract.execution_end_date:
                if contract.execution_end_date < now:
                    # Contract ended
                    if contract.is_terminated:
                        analysis["execution_performance"]["terminated"] += 1
                    else:
                        analysis["execution_performance"]["on_time"] += 1
                else:
                    # Contract still active
                    analysis["execution_performance"]["active"] += 1
            else:
                # No execution date, assume delayed
                analysis["execution_performance"]["delayed"] += 1
        
        logger.info("Supplier performance analysis completed", supplier_bin=supplier_bin)
        return analysis
    
    async def get_top_suppliers(
        self,
        limit: int = 10,
        year: int = None,
        min_contracts: int = 1,
        sort_by: str = "total_value",
    ) -> List[Dict[str, Any]]:
        """
        Get top suppliers by contract volume or value.
        
        Args:
            limit: Number of top suppliers to return
            year: Year to filter by
            min_contracts: Minimum number of contracts
            sort_by: Sort criteria (total_value, contract_count, avg_value)
            
        Returns:
            List of top suppliers with statistics
        """
        filters = {}
        if year:
            filters["year"] = year
        
        supplier_stats = await self.aggregate(
            aggregations={
                "contract_count": "count(*)",
                "total_value": "sum(sum)",
                "avg_value": "avg(sum)",
                "total_supplier_sum": "sum(supplier_sum)",
            },
            filters=filters,
            group_by=["supplier_bin", "supplier_name_ru"],
        )
        
        # Filter by minimum contracts and sort
        filtered_stats = [
            stats for stats in supplier_stats
            if stats["contract_count"] >= min_contracts
        ]
        
        # Sort by specified criteria
        if sort_by == "contract_count":
            sort_key = lambda x: x["contract_count"]
        elif sort_by == "avg_value":
            sort_key = lambda x: x["avg_value"] or 0
        else:  # total_value
            sort_key = lambda x: x["total_value"] or 0
        
        sorted_stats = sorted(filtered_stats, key=sort_key, reverse=True)
        
        return sorted_stats[:limit]
    
    # Customer Analysis
    
    async def get_customer_contracts(
        self,
        customer_bin: str,
        year: int = None,
        include_relations: bool = False,
        sort_by: str = "conclusion_date",
        sort_order: str = "desc",
    ) -> List[Contract]:
        """
        Get all contracts for a specific customer.
        
        Args:
            customer_bin: Customer BIN
            year: Year to filter by
            include_relations: Whether to include related entities
            sort_by: Field to sort by
            sort_order: Sort order
            
        Returns:
            List of customer contracts
        """
        filters = {"customer_bin": customer_bin}
        if year:
            filters["year"] = year
        
        include_rels = ["lot", "lot.trd_buy"] if include_relations else None
        
        return await self.list(
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            include_relations=include_rels,
        )
    
    # Financial Analysis
    
    async def get_contract_statistics(
        self,
        year: int = None,
        customer_bin: str = None,
        supplier_bin: str = None,
    ) -> Dict[str, Any]:
        """
        Get contract statistics.
        
        Args:
            year: Year to filter by
            customer_bin: Customer BIN to filter by
            supplier_bin: Supplier BIN to filter by
            
        Returns:
            Statistics dictionary
        """
        filters = {}
        if year:
            filters["year"] = year
        if customer_bin:
            filters["customer_bin"] = customer_bin
        if supplier_bin:
            filters["supplier_bin"] = supplier_bin
        
        # Get aggregated data
        aggregations = {
            "total_count": "count(*)",
            "total_sum": "sum(sum)",
            "avg_sum": "avg(sum)",
            "min_sum": "min(sum)",
            "max_sum": "max(sum)",
            "total_supplier_sum": "sum(supplier_sum)",
            "avg_supplier_sum": "avg(supplier_sum)",
        }
        
        results = await self.aggregate(
            aggregations=aggregations,
            filters=filters,
        )
        
        stats = results[0] if results else {}
        
        # Calculate savings if both sums are available
        if stats.get("total_sum") and stats.get("total_supplier_sum"):
            savings = stats["total_sum"] - stats["total_supplier_sum"]
            stats["total_savings"] = savings
            stats["avg_savings_percent"] = (savings / stats["total_sum"]) * 100 if stats["total_sum"] > 0 else 0
        
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
                    "total_sum": "sum(sum)",
                },
                filters=filters,
                group_by=["extract(month from conclusion_date)"],
            )
            
            stats["monthly_distribution"] = {
                int(item["extract"]): {
                    "count": item["count"],
                    "total_sum": item["total_sum"],
                }
                for item in monthly_stats
            }
        
        logger.info("Contract statistics calculated", filters=filters, stats=stats)
        return stats
    
    async def get_payment_analysis(
        self,
        year: int = None,
        customer_bin: str = None,
    ) -> Dict[str, Any]:
        """
        Analyze payment patterns and performance.
        
        Args:
            year: Year to filter by
            customer_bin: Customer BIN to filter by
            
        Returns:
            Payment analysis data
        """
        filters = {}
        if year:
            filters["year"] = year
        if customer_bin:
            filters["customer_bin"] = customer_bin
        
        # Get contracts with payment information
        contracts = await self.list(
            filters=filters,
            include_relations=["lot"],
        )
        
        analysis = {
            "total_contracts": len(contracts),
            "payment_status": {
                "completed": 0,
                "in_progress": 0,
                "overdue": 0,
                "unknown": 0,
            },
            "advance_payments": {
                "count": 0,
                "total_amount": 0,
                "avg_percent": 0,
            },
            "execution_performance": {
                "on_schedule": 0,
                "delayed": 0,
                "completed_early": 0,
            },
        }
        
        now = datetime.utcnow().date()
        total_advance_percent = 0
        advance_count = 0
        
        for contract in contracts:
            # Payment status analysis
            if contract.payment_percent == 100:
                analysis["payment_status"]["completed"] += 1
            elif contract.payment_percent and contract.payment_percent > 0:
                analysis["payment_status"]["in_progress"] += 1
            elif contract.execution_end_date and contract.execution_end_date < now:
                analysis["payment_status"]["overdue"] += 1
            else:
                analysis["payment_status"]["unknown"] += 1
            
            # Advance payment analysis
            if contract.advance_sum and contract.advance_sum > 0:
                analysis["advance_payments"]["count"] += 1
                analysis["advance_payments"]["total_amount"] += contract.advance_sum
                
                if contract.sum and contract.sum > 0:
                    advance_percent = (contract.advance_sum / contract.sum) * 100
                    total_advance_percent += advance_percent
                    advance_count += 1
            
            # Execution performance
            if contract.execution_end_date and contract.actual_end_date:
                if contract.actual_end_date <= contract.execution_end_date:
                    if contract.actual_end_date < contract.execution_end_date:
                        analysis["execution_performance"]["completed_early"] += 1
                    else:
                        analysis["execution_performance"]["on_schedule"] += 1
                else:
                    analysis["execution_performance"]["delayed"] += 1
        
        # Calculate average advance payment percentage
        if advance_count > 0:
            analysis["advance_payments"]["avg_percent"] = total_advance_percent / advance_count
        
        return analysis
    
    # Compliance and Monitoring
    
    async def get_overdue_contracts(
        self,
        days_overdue: int = 0,
        include_relations: bool = False,
    ) -> List[Contract]:
        """
        Get contracts that are overdue for completion.
        
        Args:
            days_overdue: Minimum days overdue
            include_relations: Whether to include related entities
            
        Returns:
            List of overdue contracts
        """
        cutoff_date = datetime.utcnow().date() - timedelta(days=days_overdue)
        
        filters = {
            "execution_end_date": {"lt": cutoff_date},
            "actual_end_date": None,  # Not yet completed
        }
        
        include_rels = ["lot", "lot.trd_buy"] if include_relations else None
        
        return await self.list(
            filters=filters,
            sort_by="execution_end_date",
            sort_order="asc",
            include_relations=include_rels,
        )
    
    async def get_high_value_contracts(
        self,
        min_sum: Decimal,
        year: int = None,
        include_relations: bool = False,
    ) -> List[Contract]:
        """
        Get high-value contracts above threshold.
        
        Args:
            min_sum: Minimum contract sum
            year: Year to filter by
            include_relations: Whether to include related entities
            
        Returns:
            List of high-value contracts
        """
        filters = {"sum": {"gte": min_sum}}
        if year:
            filters["year"] = year
        
        include_rels = ["lot", "lot.trd_buy"] if include_relations else None
        
        return await self.list(
            filters=filters,
            sort_by="sum",
            sort_order="desc",
            include_relations=include_rels,
        )
    
    # Validation and Business Logic
    
    async def validate_contract_data(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate contract data before creation/update.
        
        Args:
            data: Contract data
            
        Returns:
            Dictionary of validation errors
        """
        errors = {}
        
        # Required fields
        required_fields = ["goszakup_id", "contract_number", "lot_id"]
        for field in required_fields:
            if not data.get(field):
                errors.setdefault("required", []).append(f"{field} is required")
        
        # Date validation
        date_fields = [
            ("conclusion_date", "execution_start_date"),
            ("execution_start_date", "execution_end_date"),
        ]
        
        for start_field, end_field in date_fields:
            start_date = data.get(start_field)
            end_date = data.get(end_field)
            
            if start_date and end_date:
                if isinstance(start_date, str):
                    try:
                        start_date = datetime.fromisoformat(start_date).date()
                    except ValueError:
                        errors.setdefault("dates", []).append(f"Invalid {start_field} format")
                        continue
                
                if isinstance(end_date, str):
                    try:
                        end_date = datetime.fromisoformat(end_date).date()
                    except ValueError:
                        errors.setdefault("dates", []).append(f"Invalid {end_field} format")
                        continue
                
                if isinstance(start_date, date) and isinstance(end_date, date):
                    if start_date > end_date:
                        errors.setdefault("dates", []).append(
                            f"{start_field} must be before {end_field}"
                        )
        
        # Financial validation
        financial_fields = ["sum", "supplier_sum", "advance_sum"]
        for field in financial_fields:
            if data.get(field) is not None:
                try:
                    value = float(data[field])
                    if value < 0:
                        errors.setdefault("values", []).append(f"{field} must be non-negative")
                except (ValueError, TypeError):
                    errors.setdefault("values", []).append(f"Invalid {field} format")
        
        # Logical validation
        if data.get("sum") and data.get("supplier_sum"):
            try:
                contract_sum = float(data["sum"])
                supplier_sum = float(data["supplier_sum"])
                if supplier_sum > contract_sum:
                    errors.setdefault("values", []).append(
                        "Supplier sum cannot exceed contract sum"
                    )
            except (ValueError, TypeError):
                pass  # Already caught above
        
        if data.get("payment_percent") is not None:
            try:
                payment_percent = float(data["payment_percent"])
                if payment_percent < 0 or payment_percent > 100:
                    errors.setdefault("values", []).append(
                        "Payment percent must be between 0 and 100"
                    )
            except (ValueError, TypeError):
                errors.setdefault("values", []).append("Invalid payment_percent format")
        
        return errors
    
    async def check_duplicate_contract(
        self,
        goszakup_id: int,
        contract_number: str,
        exclude_id: int = None,
    ) -> Optional[Contract]:
        """
        Check for duplicate contract.
        
        Args:
            goszakup_id: Goszakup contract ID
            contract_number: Contract number
            exclude_id: ID to exclude from check (for updates)
            
        Returns:
            Existing contract if found, None otherwise
        """
        filters = {
            "or": [
                {"goszakup_id": goszakup_id},
                {"contract_number": contract_number},
            ]
        }
        
        if exclude_id:
            filters["id"] = {"ne": exclude_id}
        
        existing_contracts = await self.list(filters=filters, limit=1)
        return existing_contracts[0] if existing_contracts else None
    
    # Export and Reporting
    
    async def prepare_export_data(
        self,
        filters: Dict[str, Any] = None,
        include_lot: bool = True,
        include_procurement: bool = False,
        format_for_excel: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Prepare contract data for export.
        
        Args:
            filters: Filter criteria
            include_lot: Whether to include lot data
            include_procurement: Whether to include procurement data
            format_for_excel: Format data for Excel compatibility
            
        Returns:
            List of formatted contract data
        """
        include_relations = []
        if include_lot:
            include_relations.append("lot")
        if include_procurement:
            include_relations.append("lot.trd_buy")
        
        contracts = await self.list(
            filters=filters,
            sort_by="conclusion_date",
            sort_order="desc",
            include_relations=include_relations or None,
        )
        
        export_data = []
        
        for contract in contracts:
            # Base contract data
            row = {
                "Договор ID": contract.goszakup_id,
                "Номер договора": contract.contract_number,
                "Описание": contract.description_ru,
                "Заказчик БИН": contract.customer_bin,
                "Заказчик": contract.customer_name_ru,
                "Поставщик БИН": contract.supplier_bin,
                "Поставщик": contract.supplier_name_ru,
                "Сумма договора": contract.sum,
                "Сумма поставщика": contract.supplier_sum,
                "Дата заключения": contract.conclusion_date.isoformat() if contract.conclusion_date else None,
                "Начало исполнения": contract.execution_start_date.isoformat() if contract.execution_start_date else None,
                "Окончание исполнения": contract.execution_end_date.isoformat() if contract.execution_end_date else None,
                "Статус": contract.status_ru,
                "Процент оплаты": contract.payment_percent,
                "Авансовая сумма": contract.advance_sum,
                "Год": contract.year,
            }
            
            # Add lot data if included
            if include_lot and contract.lot:
                row.update({
                    "Лот ID": contract.lot.goszakup_id,
                    "Номер лота": contract.lot.lot_number,
                    "Описание лота": contract.lot.description_ru,
                    "КТРУ код": contract.lot.ktru_code,
                    "КТРУ наименование": contract.lot.ktru_name_ru,
                })
                
                # Add procurement data if included
                if include_procurement and contract.lot.trd_buy:
                    row.update({
                        "Закупка ID": contract.lot.trd_buy.goszakup_id,
                        "Номер закупки": contract.lot.trd_buy.number,
                        "Наименование закупки": contract.lot.trd_buy.name_ru,
                    })
            
            if format_for_excel:
                # Format dates for Excel
                date_fields = ["Дата заключения", "Начало исполнения", "Окончание исполнения"]
                for field in date_fields:
                    if row[field]:
                        try:
                            dt = datetime.fromisoformat(row[field])
                            row[field] = dt.strftime("%Y-%m-%d")
                        except:
                            pass
                
                # Format numbers for Excel
                number_fields = ["Сумма договора", "Сумма поставщика", "Авансовая сумма"]
                for field in number_fields:
                    if row[field]:
                        row[field] = f"{row[field]:,.2f}"
                
                if row["Процент оплаты"]:
                    row["Процент оплаты"] = f"{row['Процент оплаты']:.1f}%"
            
            export_data.append(row)
        
        logger.info(
            "Contract export data prepared",
            total_contracts=len(contracts),
            total_rows=len(export_data),
            include_lot=include_lot,
            include_procurement=include_procurement,
        )
        
        return export_data 