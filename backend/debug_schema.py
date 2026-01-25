
from sqlalchemy import text, inspect
from app.db.database import engine

def inspect_table():
    inspector = inspect(engine)
    table_name = 'cross_document_reconciliations'
    
    if not inspector.has_table(table_name):
        print(f"❌ Table '{table_name}' does not exist!")
        return

    print(f"✅ Table '{table_name}' exists.")
    
    # Check Columns
    columns = inspector.get_columns(table_name)
    print("\nColumns:")
    for c in columns:
        print(f"- {c['name']} ({c['type']})")

    # Check Constraints (looking for CHECK constraints on source_document)
    print("\nConstraints:")
    # SQLAlchemy inspect doesn't always show CHECK constraints easily depends on dialect
    # We can try to fetch them via raw SQL for Postgres
    
    with engine.connect() as conn:
        print("\nChecking Check Constraints via SQL:")
        sql = text(f"""
            SELECT conname, pg_get_constraintdef(oid)
            FROM pg_constraint 
            WHERE conrelid = '{table_name}'::regclass 
            AND contype = 'c';
        """)
        try:
            res = conn.execute(sql)
            for row in res:
                print(f"Constraint: {row[0]} -> {row[1]}")
        except Exception as e:
            print(f"Error checking constraints: {e}")
            
    # Check Enum types if any
    # (The column type print above usually reveals Enum('a','b'))

if __name__ == "__main__":
    inspect_table()
