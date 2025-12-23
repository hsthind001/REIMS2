"""
Seed initial data for Forensic Reconciliation Elite System

This script creates default configurations for:
- Account Risk Classes
- Health Score Configs (per persona)
- Default Materiality Configs
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal
from app.models import AccountRiskClass
from app.models import HealthScoreConfig, MaterialityConfig
from decimal import Decimal

def seed_account_risk_classes(db):
    """Seed default account risk classes"""
    risk_classes = [
        {
            'account_pattern': '1%',  # Assets
            'risk_level': 'medium',
            'description': 'Asset accounts - medium risk'
        },
        {
            'account_pattern': '2%',  # Liabilities
            'risk_level': 'high',
            'description': 'Liability accounts - high risk'
        },
        {
            'account_pattern': '3%',  # Equity
            'risk_level': 'critical',
            'description': 'Equity accounts - critical risk'
        },
        {
            'account_pattern': '4%',  # Revenue
            'risk_level': 'high',
            'description': 'Revenue accounts - high risk'
        },
        {
            'account_pattern': '5%',  # Expenses
            'risk_level': 'medium',
            'description': 'Expense accounts - medium risk'
        },
        {
            'account_pattern': '9%',  # Net Income
            'risk_level': 'critical',
            'description': 'Net income accounts - critical risk'
        },
        {
            'account_pattern': '1000-0000',  # Cash
            'risk_level': 'critical',
            'description': 'Cash account - critical risk'
        },
        {
            'account_pattern': '2000-0000',  # Accounts Payable
            'risk_level': 'high',
            'description': 'Accounts payable - high risk'
        },
    ]
    
    for risk_data in risk_classes:
        existing = db.query(AccountRiskClass).filter(
            AccountRiskClass.account_pattern == risk_data['account_pattern']
        ).first()
        
        if not existing:
            risk_class = AccountRiskClass(**risk_data)
            db.add(risk_class)
            print(f"  ✅ Created risk class: {risk_data['account_pattern']} ({risk_data['risk_level']})")
        else:
            print(f"  ⏭️  Risk class already exists: {risk_data['account_pattern']}")
    
    db.commit()

def seed_health_score_configs(db):
    """Seed health score configs for different personas"""
    personas = [
        {
            'persona': 'auditor',
            'weights_json': {
                'approval_score': 0.4,
                'confidence_score': 0.3,
                'discrepancy_penalty': 0.3
            },
            'trend_weight': Decimal('0.05'),
            'volatility_weight': Decimal('0.05'),
            'blocked_close_rules': []
        },
        {
            'persona': 'controller',
            'weights_json': {
                'approval_score': 0.5,
                'confidence_score': 0.3,
                'discrepancy_penalty': 0.2
            },
            'trend_weight': Decimal('0.1'),
            'volatility_weight': Decimal('0.05'),
            'blocked_close_rules': ['covenant_violation', 'material_discrepancy']
        },
        {
            'persona': 'analyst',
            'weights_json': {
                'approval_score': 0.3,
                'confidence_score': 0.4,
                'discrepancy_penalty': 0.3
            },
            'trend_weight': Decimal('0.15'),
            'volatility_weight': Decimal('0.1'),
            'blocked_close_rules': []
        },
        {
            'persona': 'investor',
            'weights_json': {
                'approval_score': 0.4,
                'confidence_score': 0.4,
                'discrepancy_penalty': 0.2
            },
            'trend_weight': Decimal('0.2'),
            'volatility_weight': Decimal('0.1'),
            'blocked_close_rules': ['material_discrepancy']
        }
    ]
    
    for persona_data in personas:
        existing = db.query(HealthScoreConfig).filter(
            HealthScoreConfig.persona == persona_data['persona']
        ).first()
        
        if not existing:
            config = HealthScoreConfig(**persona_data)
            db.add(config)
            print(f"  ✅ Created health score config: {persona_data['persona']}")
        else:
            print(f"  ⏭️  Health score config already exists: {persona_data['persona']}")
    
    db.commit()

def seed_default_materiality_configs(db):
    """Seed default materiality configs"""
    # Get first property if exists
    from app.models.property import Property
    first_property = db.query(Property).first()
    
    if not first_property:
        print("  ⚠️  No properties found. Skipping materiality config seeding.")
        return
    
    materiality_configs = [
        {
            'property_id': first_property.id,
            'statement_type': 'balance_sheet',
            'absolute_threshold': Decimal('1000.00'),
            'relative_threshold_percent': Decimal('1.0'),
            'risk_class_weights': {
                'critical': 0.5,
                'high': 1.0,
                'medium': 2.0,
                'low': 5.0
            }
        },
        {
            'property_id': first_property.id,
            'statement_type': 'income_statement',
            'absolute_threshold': Decimal('500.00'),
            'relative_threshold_percent': Decimal('0.5'),
            'risk_class_weights': {
                'critical': 0.25,
                'high': 0.5,
                'medium': 1.0,
                'low': 2.0
            }
        }
    ]
    
    for config_data in materiality_configs:
        existing = db.query(MaterialityConfig).filter(
            MaterialityConfig.property_id == config_data['property_id'],
            MaterialityConfig.statement_type == config_data['statement_type']
        ).first()
        
        if not existing:
            config = MaterialityConfig(**config_data)
            db.add(config)
            print(f"  ✅ Created materiality config: {config_data['statement_type']} for property {config_data['property_id']}")
        else:
            print(f"  ⏭️  Materiality config already exists: {config_data['statement_type']}")
    
    db.commit()

def main():
    """Main seeding function"""
    print("🌱 Seeding Forensic Reconciliation Elite System data...")
    print()
    
    db = SessionLocal()
    try:
        print("1. Seeding Account Risk Classes...")
        seed_account_risk_classes(db)
        print()
        
        print("2. Seeding Health Score Configs...")
        seed_health_score_configs(db)
        print()
        
        print("3. Seeding Default Materiality Configs...")
        seed_default_materiality_configs(db)
        print()
        
        print("✅ Seeding complete!")
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    main()

