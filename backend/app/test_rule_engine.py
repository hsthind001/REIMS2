import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.services.reconciliation_rule_engine import ReconciliationRuleEngine
from app.core.config import settings

# Create async engine for testing
# Using the same DB URL from settings but async
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def test_engine():
    async with AsyncSessionLocal() as db:
        print("\n--- Starting Reconciliation Rule Engine Test ---")
        
        # Initialize Engine
        rule_engine = ReconciliationRuleEngine(db)
        
        # Test Parameters
        PROPERTY_ID = 11
        PERIOD_ID = 169
        
        print(f"Executing rules for Property {PROPERTY_ID}, Period {PERIOD_ID}...")
        
        # Execute Rules
        results = await rule_engine.execute_all_rules(PROPERTY_ID, PERIOD_ID)
        
        print(f"\nExecution Complete. Total Rules Executed: {len(results)}")
        
        # Analysis
        pass_count = sum(1 for r in results if r.status == "PASS")
        fail_count = sum(1 for r in results if r.status == "FAIL")
        
        print(f"PASS: {pass_count}")
        print(f"FAIL: {fail_count}")
        
        print("\n--- Detailed Results ---")
        for res in results:
            print(f"[{res.status}] {res.rule_id} {res.rule_name}: {res.details}")
            if res.status == "FAIL":
                print(f"    Diff: {res.difference} (Src: {res.source_value}, Tgt: {res.target_value})")

        # Save Results
        print("\nSaving results to database...")
        await rule_engine.save_results()
        print("Save completed.")

if __name__ == "__main__":
    asyncio.run(test_engine())
