import sys
import os
from sqlalchemy import text

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.db.database import SessionLocal

def export_reconciliations():
    print("Initializing DB Session...")
    db = SessionLocal()
    
    try:
        print("Fetching reconciliation results...")
        # Get all results for our demo property
        query = text("""
            SELECT 
                property_id, period_id, reconciliation_type, rule_code, status,
                source_document, target_document, source_value, target_value, 
                difference, materiality_threshold, is_material, explanation, 
                recommendation
            FROM cross_document_reconciliations
            WHERE property_id = 11 AND period_id = 169
        """)
        
        results = db.execute(query).fetchall()
        print(f"Found {len(results)} records.")
        
        sql_content = "-- Seed file for verified reconciliation results (Property 11, Period 169)\n"
        sql_content += "-- Generated automatically for persistence\n\n"
        
        sql_content += "DELETE FROM cross_document_reconciliations WHERE property_id = 11 AND period_id = 169;\n\n"
        
        for row in results:
            # Escape strings
            expl = row.explanation.replace("'", "''") if row.explanation else ""
            rec = row.recommendation.replace("'", "''") if row.recommendation else "NULL"
            if rec != "NULL":
                rec = f"'{rec}'"
            
            # Format numbers
            src = f"{row.source_value:.2f}"
            tgt = f"{row.target_value:.2f}"
            diff = f"{row.difference:.2f}"
            thresh = f"{row.materiality_threshold:.2f}"
            
            sql = f"""INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    {row.property_id}, {row.period_id}, '{row.reconciliation_type}', '{row.rule_code}', '{row.status}',
    '{row.source_document}', '{row.target_document}', {src}, {tgt},
    {diff}, {thresh}, {'TRUE' if row.is_material else 'FALSE'}, '{expl}', {rec},
    NOW(), NOW()
);\n"""
            sql_content += sql

        output_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', '06_verified_reconciliations.sql')
        
        with open(output_path, 'w') as f:
            f.write(sql_content)
            
        print(f"Successfully exported {len(results)} records to {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    export_reconciliations()
