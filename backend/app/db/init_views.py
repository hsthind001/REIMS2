"""
Database View Initialization

Executes views.sql to create all financial reporting views
"""
from sqlalchemy import text
from sqlalchemy.engine import Engine
import os


def create_database_views(engine: Engine) -> dict:
    """
    Create all database views from views.sql
    
    Args:
        engine: SQLAlchemy engine
    
    Returns:
        Dict with success status and views created
    """
    views_created = []
    errors = []
    
    try:
        # Get path to views.sql
        current_dir = os.path.dirname(os.path.abspath(__file__))
        views_sql_path = os.path.join(current_dir, 'views.sql')
        
        # Read SQL file
        with open(views_sql_path, 'r') as f:
            sql_content = f.read()
        
        # Split by CREATE OR REPLACE VIEW statements
        # Each view is a separate statement
        view_statements = []
        current_statement = []
        
        for line in sql_content.split('\n'):
            # Skip comments and empty lines
            if line.strip().startswith('--') or not line.strip():
                if line.strip().startswith('-- ====='):
                    # Section separator
                    if current_statement:
                        view_statements.append('\n'.join(current_statement))
                        current_statement = []
                continue
            
            current_statement.append(line)
        
        # Add last statement
        if current_statement:
            view_statements.append('\n'.join(current_statement))
        
        # Execute each view creation with proper error handling
        with engine.connect() as conn:
            for statement in view_statements:
                if 'CREATE OR REPLACE VIEW' in statement:
                    try:
                        # Extract view name first
                        view_name = statement.split('VIEW')[1].split('AS')[0].strip()
                        
                        # Drop view first if it exists (to avoid column drop errors)
                        try:
                            conn.execute(text(f"DROP VIEW IF EXISTS {view_name} CASCADE"))
                            conn.commit()
                        except Exception as drop_error:
                            # Ignore drop errors, view might not exist
                            conn.rollback()
                        
                        # Now create/replace the view
                        conn.execute(text(statement))
                        conn.commit()
                        views_created.append(view_name)
                        
                    except Exception as e:
                        # Rollback transaction on error
                        try:
                            conn.rollback()
                        except:
                            pass
                        error_msg = f"Failed to create view {view_name if 'view_name' in locals() else 'unknown'}: {str(e)[:100]}"
                        errors.append(error_msg)
                        print(f"Error creating view: {e}")
        
        return {
            "success": len(errors) == 0,
            "views_created": views_created,
            "total_views": len(views_created),
            "errors": errors
        }
    
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"views.sql not found at {views_sql_path}",
            "views_created": [],
            "total_views": 0
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "views_created": views_created,
            "total_views": len(views_created),
            "errors": errors
        }


def drop_all_views(engine: Engine) -> dict:
    """
    Drop all database views
    
    Useful for cleanup or re-initialization
    """
    views_to_drop = [
        'v_property_financial_summary',
        'v_monthly_comparison',
        'v_ytd_rollup',
        'v_multi_property_comparison',
        'v_extraction_quality_dashboard',
        'v_validation_issues',
        'v_lease_expiration_pipeline',
        'v_annual_trends',
        'v_portfolio_summary',
    ]
    
    dropped = []
    errors = []
    
    with engine.connect() as conn:
        for view_name in views_to_drop:
            try:
                conn.execute(text(f"DROP VIEW IF EXISTS {view_name} CASCADE"))
                conn.commit()
                dropped.append(view_name)
            except Exception as e:
                errors.append(f"{view_name}: {str(e)}")
    
    return {
        "success": len(errors) == 0,
        "views_dropped": dropped,
        "total_dropped": len(dropped),
        "errors": errors
    }

