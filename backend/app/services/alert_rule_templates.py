"""
Alert Rule Templates
Pre-built rule templates for common alert scenarios
"""
from typing import Dict, List, Any, Optional


class AlertRuleTemplates:
    """Pre-built alert rule templates"""
    
    TEMPLATES = [
        {
            "id": "dscr_threshold_breach",
            "name": "DSCR Threshold Breach",
            "description": "Alert when Debt Service Coverage Ratio falls below threshold",
            "rule_type": "threshold",
            "field_name": "dscr",
            "condition": "less_than",
            "default_threshold": 1.25,
            "default_severity": "critical",
            "severity_mapping": {
                "critical_threshold": 0.2,  # 20% below threshold
                "high_threshold": 0.1,  # 10% below threshold
                "warning_threshold": 0.05  # 5% below threshold
            },
            "assigned_committee": "FINANCE_SUBCOMMITTEE",
            "alert_type": "DSCR_BREACH"
        },
        {
            "id": "occupancy_rate_warning",
            "name": "Occupancy Rate Warning",
            "description": "Alert when occupancy rate drops below threshold",
            "rule_type": "threshold",
            "field_name": "occupancy_rate",
            "condition": "less_than",
            "default_threshold": 85.0,
            "default_severity": "warning",
            "severity_mapping": {
                "critical_threshold": 0.15,  # 15% below threshold
                "high_threshold": 0.1,  # 10% below threshold
                "warning_threshold": 0.05  # 5% below threshold
            },
            "assigned_committee": "OCCUPANCY_SUBCOMMITTEE",
            "alert_type": "OCCUPANCY_WARNING"
        },
        {
            "id": "ltv_breach",
            "name": "LTV Ratio Breach",
            "description": "Alert when Loan-to-Value ratio exceeds threshold",
            "rule_type": "threshold",
            "field_name": "ltv",
            "condition": "greater_than",
            "default_threshold": 0.75,
            "default_severity": "high",
            "severity_mapping": {
                "critical_threshold": 0.15,  # 15% above threshold
                "high_threshold": 0.1,  # 10% above threshold
                "warning_threshold": 0.05  # 5% above threshold
            },
            "assigned_committee": "RISK_COMMITTEE",
            "alert_type": "LTV_BREACH"
        },
        {
            "id": "revenue_decline",
            "name": "Revenue Decline Detection",
            "description": "Alert when revenue declines significantly",
            "rule_type": "statistical",
            "field_name": "total_revenue",
            "condition": "percentage_change",
            "default_threshold": 10.0,  # 10% decline
            "default_severity": "warning",
            "severity_mapping": {
                "critical_threshold": 0.3,  # 30% decline
                "high_threshold": 0.2,  # 20% decline
                "warning_threshold": 0.1  # 10% decline
            },
            "assigned_committee": "FINANCE_SUBCOMMITTEE",
            "alert_type": "REVENUE_DECLINE"
        },
        {
            "id": "expense_spike",
            "name": "Expense Spike Detection",
            "description": "Alert when expenses increase significantly",
            "rule_type": "statistical",
            "field_name": "total_operating_expenses",
            "condition": "percentage_change",
            "default_threshold": 15.0,  # 15% increase
            "default_severity": "warning",
            "severity_mapping": {
                "critical_threshold": 0.3,  # 30% increase
                "high_threshold": 0.2,  # 20% increase
                "warning_threshold": 0.15  # 15% increase
            },
            "assigned_committee": "FINANCE_SUBCOMMITTEE",
            "alert_type": "EXPENSE_SPIKE"
        },
        {
            "id": "cash_flow_negative",
            "name": "Negative Cash Flow",
            "description": "Alert when operating cash flow becomes negative",
            "rule_type": "threshold",
            "field_name": "operating_cash_flow",
            "condition": "less_than",
            "default_threshold": 0.0,
            "default_severity": "critical",
            "assigned_committee": "FINANCE_SUBCOMMITTEE",
            "alert_type": "CASH_FLOW_NEGATIVE"
        },
        {
            "id": "liquidity_warning",
            "name": "Liquidity Ratio Warning",
            "description": "Alert when current ratio falls below threshold",
            "rule_type": "threshold",
            "field_name": "current_ratio",
            "condition": "less_than",
            "default_threshold": 1.0,
            "default_severity": "warning",
            "severity_mapping": {
                "critical_threshold": 0.3,  # 30% below threshold
                "high_threshold": 0.2,  # 20% below threshold
                "warning_threshold": 0.1  # 10% below threshold
            },
            "assigned_committee": "RISK_COMMITTEE",
            "alert_type": "LIQUIDITY_WARNING"
        },
        {
            "id": "debt_to_equity_breach",
            "name": "Debt-to-Equity Breach",
            "description": "Alert when debt-to-equity ratio exceeds threshold",
            "rule_type": "threshold",
            "field_name": "debt_to_equity_ratio",
            "condition": "greater_than",
            "default_threshold": 2.0,
            "default_severity": "high",
            "severity_mapping": {
                "critical_threshold": 0.5,  # 50% above threshold
                "high_threshold": 0.3,  # 30% above threshold
                "warning_threshold": 0.15  # 15% above threshold
            },
            "assigned_committee": "RISK_COMMITTEE",
            "alert_type": "DEBT_TO_EQUITY_BREACH"
        },
        {
            "id": "debt_yield_breach",
            "name": "Debt Yield Breach",
            "description": "Alert when debt yield falls below threshold",
            "rule_type": "threshold",
            "field_name": "debt_yield",
            "condition": "less_than",
            "default_threshold": 0.08,  # 8%
            "default_severity": "high",
            "severity_mapping": {
                "critical_threshold": 0.25,  # 25% below threshold
                "high_threshold": 0.15,  # 15% below threshold
                "warning_threshold": 0.1  # 10% below threshold
            },
            "assigned_committee": "FINANCE_SUBCOMMITTEE",
            "alert_type": "DEBT_YIELD_BREACH"
        },
        {
            "id": "interest_coverage_breach",
            "name": "Interest Coverage Breach",
            "description": "Alert when interest coverage ratio falls below threshold",
            "rule_type": "threshold",
            "field_name": "interest_coverage_ratio",
            "condition": "less_than",
            "default_threshold": 1.5,
            "default_severity": "critical",
            "severity_mapping": {
                "critical_threshold": 0.3,  # 30% below threshold
                "high_threshold": 0.2,  # 20% below threshold
                "warning_threshold": 0.1  # 10% below threshold
            },
            "assigned_committee": "FINANCE_SUBCOMMITTEE",
            "alert_type": "INTEREST_COVERAGE_BREACH"
        },
        {
            "id": "break_even_occupancy_breach",
            "name": "Break-Even Occupancy Breach",
            "description": "Alert when occupancy falls below break-even point",
            "rule_type": "threshold",
            "field_name": "break_even_occupancy",
            "condition": "less_than",
            "default_threshold": 0.0,  # Will be calculated
            "default_severity": "critical",
            "assigned_committee": "OCCUPANCY_SUBCOMMITTEE",
            "alert_type": "BREAK_EVEN_OCCUPANCY_BREACH"
        },
        {
            "id": "rent_collection_rate",
            "name": "Rent Collection Rate Warning",
            "description": "Alert when rent collection rate falls below threshold",
            "rule_type": "threshold",
            "field_name": "rent_collection_rate",
            "condition": "less_than",
            "default_threshold": 95.0,  # 95%
            "default_severity": "warning",
            "severity_mapping": {
                "critical_threshold": 0.1,  # 10% below threshold
                "high_threshold": 0.05,  # 5% below threshold
                "warning_threshold": 0.02  # 2% below threshold
            },
            "assigned_committee": "OCCUPANCY_SUBCOMMITTEE",
            "alert_type": "RENT_COLLECTION_RATE"
        }
    ]
    
    @classmethod
    def get_all_templates(cls) -> List[Dict[str, Any]]:
        """Get all available rule templates"""
        return cls.TEMPLATES
    
    @classmethod
    def get_template(cls, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific template by ID"""
        for template in cls.TEMPLATES:
            if template["id"] == template_id:
                return template
        return None
    
    @classmethod
    def create_rule_from_template(
        cls,
        template_id: str,
        property_id: Optional[int] = None,
        threshold_override: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create rule configuration from template
        
        Args:
            template_id: Template ID
            property_id: If provided, creates property-specific rule
            threshold_override: Override default threshold
        
        Returns:
            Rule configuration dict ready for AlertRule creation
        """
        template = cls.get_template(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' not found")
        
        config = {
            "rule_name": template["name"],
            "description": template["description"],
            "rule_type": template["rule_type"],
            "field_name": template["field_name"],
            "condition": template["condition"],
            "threshold_value": threshold_override or template["default_threshold"],
            "severity": template["default_severity"],
            "is_active": True,
            "severity_mapping": template.get("severity_mapping"),
            "cooldown_period": 60,  # Default 1 hour
            "property_specific": property_id is not None,
            "property_id": property_id,
            "rule_template_id": None,  # Will be set when saved
            "rule_expression": {
                "template_id": template_id,
                "alert_type": template.get("alert_type"),
                "assigned_committee": template.get("assigned_committee")
            }
        }
        
        return config

