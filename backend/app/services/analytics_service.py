"""
Analytics Service

Service for complex data analysis and business intelligence.
Provides dashboard analytics, trends, and insights.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from sqlalchemy import and_, or_, func, desc, asc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.trd_buy import TrdBuy
from app.models.lot import Lot
from app.models.contract import Contract
from app.models.participant import Participant
from app.services.base_service import BaseService
import structlog

logger = structlog.get_logger()


class AnalyticsService:
    """
    Analytics service for business intelligence and reporting.
    
    Features:
    - Cross-entity analytics
    - Market trends analysis
    - Performance dashboards
    - Competitive intelligence
    """
    
    def __init__(self, session: AsyncSession = None):
        """Initialize Analytics service."""
        self.session = session
    
    # Dashboard Analytics
    
    async def get_dashboard_summary(
        self,
        year: int = None,
        region: str = None,
    ) -> Dict[str, Any]:
        """
        Get high-level dashboard summary statistics.
        
        Args:
            year: Year to filter by
            region: Region to filter by
            
        Returns:
            Dashboard summary data
        """
        if not year:
            year = datetime.now().year
        
        # Base filters
        filters = {"year": year}
        if region:
            filters["region_ru"] = region
        
        # Get summary statistics
        from app.services.trd_buy_service import TrdBuyService
        from app.services.contract_service import ContractService
        from app.services.participant_service import ParticipantService
        
        trd_buy_service = TrdBuyService(self.session)
        contract_service = ContractService(self.session)
        participant_service = ParticipantService(self.session)
        
        # Procurement statistics
        procurement_stats = await trd_buy_service.get_procurement_stats(year=year)
        
        # Contract statistics
        contract_stats = await contract_service.get_contract_statistics(year=year)
        
        # Participant statistics
        participant_stats = await participant_service.get_participant_statistics(region=region)
        
        # Market concentration
        top_customers = await trd_buy_service.get_top_customers(limit=5, year=year)
        top_suppliers = await contract_service.get_top_suppliers(limit=5, year=year)
        
        summary = {
            "period": {
                "year": year,
                "region": region,
                "last_updated": datetime.utcnow().isoformat(),
            },
            "procurement_overview": {
                "total_procurements": procurement_stats.get("total_count", 0),
                "total_value": procurement_stats.get("total_value", 0),
                "avg_value": procurement_stats.get("avg_value", 0),
                "active_procurements": procurement_stats.get("active_count", 0),
            },
            "contract_overview": {
                "total_contracts": contract_stats.get("total_count", 0),
                "total_value": contract_stats.get("total_value", 0),
                "execution_rate": contract_stats.get("execution_rate", 0),
                "avg_contract_value": contract_stats.get("avg_value", 0),
            },
            "market_participants": {
                "total_participants": participant_stats.get("total_count", 0),
                "active_suppliers": participant_stats.get("active_count", 0),
                "government_entities": participant_stats.get("government_count", 0),
                "sme_participants": participant_stats.get("sme_count", 0),
            },
            "market_leaders": {
                "top_customers": top_customers,
                "top_suppliers": top_suppliers,
            },
            "health_indicators": {
                "blacklisted_participants": participant_stats.get("blacklisted_count", 0),
                "completion_rate": contract_stats.get("completion_rate", 0),
                "avg_procurement_duration": procurement_stats.get("avg_duration_days", 0),
            },
        }
        
        logger.info("Dashboard summary generated", year=year, region=region)
        return summary
    
    async def get_market_trends(
        self,
        months: int = 12,
        category: str = None,
    ) -> Dict[str, Any]:
        """
        Analyze market trends over time.
        
        Args:
            months: Number of months to analyze
            category: KTRU category to focus on
            
        Returns:
            Market trends analysis
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        
        # This would require complex SQL queries
        # For now, return structure with placeholder data
        trends = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "months": months,
                "category": category,
            },
            "procurement_trends": {
                "monthly_volume": [],  # List of {month, count, value}
                "growth_rate": 0,
                "seasonal_patterns": [],
            },
            "price_trends": {
                "monthly_avg_prices": [],  # List of {month, avg_price, category}
                "inflation_rate": 0,
                "price_volatility": 0,
            },
            "competition_trends": {
                "avg_participants_per_tender": 0,
                "competition_index": 0,
                "market_concentration": 0,
            },
            "efficiency_trends": {
                "avg_procurement_duration": 0,
                "success_rate": 0,
                "cancellation_rate": 0,
            },
        }
        
        # TODO: Implement actual trend calculations
        logger.info("Market trends analysis completed", months=months, category=category)
        return trends
    
    async def get_regional_comparison(
        self,
        year: int = None,
        metric: str = "volume",
    ) -> List[Dict[str, Any]]:
        """
        Compare regions by various metrics.
        
        Args:
            year: Year to analyze
            metric: Metric to compare (volume, value, efficiency)
            
        Returns:
            Regional comparison data
        """
        if not year:
            year = datetime.now().year
        
        # Get regional statistics
        from app.services.participant_service import ParticipantService
        participant_service = ParticipantService(self.session)
        
        regional_stats = await participant_service.get_regional_statistics()
        
        # Enhance with procurement and contract data
        # This would require joins across services
        comparison = []
        
        for region_data in regional_stats:
            region_name = region_data.get("region_ru", "Unknown")
            
            enhanced_data = {
                "region": region_name,
                "participants": {
                    "total": region_data.get("participant_count", 0),
                    "active": region_data.get("active_count", 0),
                    "sme": region_data.get("sme_count", 0),
                },
                "procurement_activity": {
                    "total_procurements": 0,  # TODO: Calculate from TrdBuy
                    "total_value": 0,
                    "avg_value": 0,
                },
                "contract_performance": {
                    "total_contracts": 0,  # TODO: Calculate from Contract
                    "execution_rate": 0,
                    "avg_duration": 0,
                },
                "efficiency_metrics": {
                    "competition_index": 0,
                    "success_rate": 0,
                    "time_to_contract": 0,
                },
                "rankings": {
                    f"{metric}_rank": 0,
                    "overall_rank": 0,
                },
            }
            
            comparison.append(enhanced_data)
        
        # Sort by the specified metric
        # TODO: Implement actual sorting logic based on metric
        comparison.sort(key=lambda x: x["participants"]["total"], reverse=True)
        
        # Add rankings
        for i, region in enumerate(comparison):
            region["rankings"]["overall_rank"] = i + 1
        
        logger.info("Regional comparison completed", year=year, metric=metric, regions=len(comparison))
        return comparison
    
    async def get_supplier_performance_analysis(
        self,
        supplier_bin: str = None,
        top_n: int = 20,
        year: int = None,
    ) -> Dict[str, Any]:
        """
        Analyze supplier performance across the market.
        
        Args:
            supplier_bin: Specific supplier to analyze
            top_n: Number of top suppliers to include
            year: Year to analyze
            
        Returns:
            Supplier performance analysis
        """
        if not year:
            year = datetime.now().year
        
        from app.services.contract_service import ContractService
        contract_service = ContractService(self.session)
        
        if supplier_bin:
            # Analyze specific supplier
            supplier_analysis = await contract_service.analyze_supplier_performance(supplier_bin)
            
            analysis = {
                "type": "individual",
                "supplier_bin": supplier_bin,
                "analysis": supplier_analysis,
                "benchmarks": {
                    "market_avg_execution_rate": 0,  # TODO: Calculate market average
                    "market_avg_contract_value": 0,
                    "market_avg_duration": 0,
                },
                "recommendations": self._generate_supplier_recommendations(supplier_analysis),
            }
        else:
            # Market-wide analysis
            top_suppliers = await contract_service.get_top_suppliers(limit=top_n, year=year)
            
            analysis = {
                "type": "market",
                "year": year,
                "top_suppliers": top_suppliers,
                "market_metrics": {
                    "total_suppliers": len(top_suppliers),
                    "market_concentration": self._calculate_market_concentration(top_suppliers),
                    "avg_performance_score": 0,
                },
                "insights": self._generate_market_insights(top_suppliers),
            }
        
        logger.info("Supplier performance analysis completed", supplier_bin=supplier_bin, year=year)
        return analysis
    
    async def get_procurement_efficiency_report(
        self,
        year: int = None,
        customer_bin: str = None,
    ) -> Dict[str, Any]:
        """
        Generate procurement efficiency report.
        
        Args:
            year: Year to analyze
            customer_bin: Specific customer to analyze
            
        Returns:
            Efficiency report
        """
        if not year:
            year = datetime.now().year
        
        from app.services.trd_buy_service import TrdBuyService
        from app.services.contract_service import ContractService
        
        trd_buy_service = TrdBuyService(self.session)
        contract_service = ContractService(self.session)
        
        # Get procurement statistics
        procurement_stats = await trd_buy_service.get_procurement_stats(year=year, customer_bin=customer_bin)
        
        # Get contract statistics  
        contract_stats = await contract_service.get_contract_statistics(year=year, customer_bin=customer_bin)
        
        efficiency_report = {
            "period": {
                "year": year,
                "customer_bin": customer_bin,
                "report_date": datetime.utcnow().isoformat(),
            },
            "process_efficiency": {
                "avg_procurement_duration": procurement_stats.get("avg_duration_days", 0),
                "time_to_contract": 0,  # Days from procurement to contract
                "success_rate": procurement_stats.get("success_rate", 0),
                "cancellation_rate": procurement_stats.get("cancellation_rate", 0),
            },
            "cost_efficiency": {
                "avg_savings_rate": 0,  # Planned vs actual cost
                "cost_per_procurement": 0,
                "budget_utilization": 0,
            },
            "competition_metrics": {
                "avg_participants": procurement_stats.get("avg_participants", 0),
                "competition_rate": 0,  # % of procurements with >1 participant
                "monopoly_rate": 0,  # % of single-participant procurements
            },
            "quality_metrics": {
                "contract_execution_rate": contract_stats.get("execution_rate", 0),
                "on_time_delivery_rate": 0,
                "supplier_satisfaction": 0,
            },
            "recommendations": self._generate_efficiency_recommendations(procurement_stats, contract_stats),
        }
        
        logger.info("Efficiency report generated", year=year, customer_bin=customer_bin)
        return efficiency_report
    
    async def get_risk_analysis(
        self,
        entity_type: str = "market",
        entity_id: str = None,
    ) -> Dict[str, Any]:
        """
        Perform risk analysis for market or specific entity.
        
        Args:
            entity_type: Type of analysis (market, customer, supplier)
            entity_id: Specific entity ID (BIN)
            
        Returns:
            Risk analysis report
        """
        from app.services.participant_service import ParticipantService
        participant_service = ParticipantService(self.session)
        
        risk_analysis = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "analysis_date": datetime.utcnow().isoformat(),
            "risk_scores": {
                "overall_risk": 0,  # 0-100 scale
                "financial_risk": 0,
                "operational_risk": 0,
                "compliance_risk": 0,
                "market_risk": 0,
            },
            "risk_factors": [],
            "recommendations": [],
        }
        
        if entity_type == "market":
            # Market-wide risk analysis
            blacklisted_stats = await participant_service.get_participant_statistics()
            blacklisted_rate = blacklisted_stats.get("blacklisted_percent", 0)
            
            if blacklisted_rate > 5:
                risk_analysis["risk_factors"].append({
                    "type": "compliance",
                    "severity": "high" if blacklisted_rate > 10 else "medium",
                    "description": f"High blacklist rate: {blacklisted_rate:.1f}%",
                })
        
        elif entity_type in ["customer", "supplier"]:
            # Entity-specific risk analysis
            if entity_id:
                compliance = await participant_service.get_compliance_status(entity_id)
                
                if compliance.get("status", {}).get("is_blacklisted"):
                    risk_analysis["risk_factors"].append({
                        "type": "compliance",
                        "severity": "critical",
                        "description": "Entity is blacklisted",
                    })
        
        # Calculate overall risk score
        risk_analysis["risk_scores"]["overall_risk"] = self._calculate_overall_risk(risk_analysis["risk_factors"])
        
        logger.info("Risk analysis completed", entity_type=entity_type, entity_id=entity_id)
        return risk_analysis
    
    # Helper Methods
    
    def _generate_supplier_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations for supplier performance."""
        recommendations = []
        
        performance = analysis.get("performance_metrics", {})
        execution_rate = performance.get("execution_rate", 0)
        
        if execution_rate < 80:
            recommendations.append("Improve contract execution rate - currently below market standards")
        
        if performance.get("avg_contract_value", 0) < 1000000:  # 1M tenge
            recommendations.append("Consider pursuing larger contracts to improve market position")
        
        return recommendations
    
    def _generate_market_insights(self, suppliers: List[Dict[str, Any]]) -> List[str]:
        """Generate insights from market data."""
        insights = []
        
        if len(suppliers) > 0:
            insights.append(f"Market led by {len(suppliers)} major suppliers")
        
        # Calculate concentration
        if len(suppliers) >= 3:
            top3_share = sum(s.get("total_value", 0) for s in suppliers[:3])
            total_market = sum(s.get("total_value", 0) for s in suppliers)
            
            if total_market > 0:
                concentration = (top3_share / total_market) * 100
                if concentration > 60:
                    insights.append(f"High market concentration - top 3 suppliers control {concentration:.1f}% of market")
        
        return insights
    
    def _calculate_market_concentration(self, suppliers: List[Dict[str, Any]]) -> float:
        """Calculate market concentration index."""
        if not suppliers:
            return 0
        
        total_value = sum(s.get("total_value", 0) for s in suppliers)
        if total_value == 0:
            return 0
        
        # Herfindahl-Hirschman Index
        hhi = sum((s.get("total_value", 0) / total_value) ** 2 for s in suppliers)
        return hhi * 10000  # Convert to standard HHI scale
    
    def _generate_efficiency_recommendations(
        self,
        procurement_stats: Dict[str, Any],
        contract_stats: Dict[str, Any],
    ) -> List[str]:
        """Generate efficiency improvement recommendations."""
        recommendations = []
        
        duration = procurement_stats.get("avg_duration_days", 0)
        if duration > 30:
            recommendations.append("Reduce procurement duration - currently above recommended 30 days")
        
        success_rate = procurement_stats.get("success_rate", 0)
        if success_rate < 80:
            recommendations.append("Improve procurement success rate through better planning")
        
        execution_rate = contract_stats.get("execution_rate", 0)
        if execution_rate < 90:
            recommendations.append("Enhance contract execution monitoring and supplier management")
        
        return recommendations
    
    def _calculate_overall_risk(self, risk_factors: List[Dict[str, Any]]) -> int:
        """Calculate overall risk score from individual factors."""
        if not risk_factors:
            return 10  # Low risk
        
        severity_weights = {
            "low": 10,
            "medium": 25,
            "high": 50,
            "critical": 80,
        }
        
        total_score = sum(severity_weights.get(factor.get("severity", "low"), 10) for factor in risk_factors)
        return min(total_score, 100)  # Cap at 100
    
    # Export Methods
    
    async def prepare_analytics_export(
        self,
        report_type: str,
        parameters: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Prepare analytics data for export.
        
        Args:
            report_type: Type of report to export
            parameters: Report parameters
            
        Returns:
            List of formatted data for export
        """
        if report_type == "dashboard_summary":
            summary = await self.get_dashboard_summary(**parameters or {})
            return [self._flatten_dict(summary)]
        
        elif report_type == "regional_comparison":
            comparison = await self.get_regional_comparison(**parameters or {})
            return comparison
        
        elif report_type == "efficiency_report":
            report = await self.get_procurement_efficiency_report(**parameters or {})
            return [self._flatten_dict(report)]
        
        else:
            logger.warning("Unknown report type requested", report_type=report_type)
            return []
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = "", sep: str = "_") -> Dict[str, Any]:
        """Flatten nested dictionary for Excel export."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items) 