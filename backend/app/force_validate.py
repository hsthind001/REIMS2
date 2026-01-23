import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.db.database import SessionLocal
from app.services.forensic_reconciliation_service import ForensicReconciliationService
from app.models.forensic_reconciliation_session import ForensicReconciliationSession

def force_validate():
    print("Initializing DB Session...")
    db = SessionLocal()
    
    try:
        # Find the latest session for Property 11, Period 169
        session = db.query(ForensicReconciliationSession).filter(
            ForensicReconciliationSession.property_id == 11,
            ForensicReconciliationSession.period_id == 169
        ).order_by(ForensicReconciliationSession.id.desc()).first()
        
        if not session:
            print("No session found for Property 11, Period 169!")
            return

        print(f"Found Session ID: {session.id}")
        
        service = ForensicReconciliationService(db)
        print(f"Validating matches for Session {session.id}...")
        
        result = service.validate_matches(session_id=session.id)
        
        print("Validation Result:")
        print(result)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    force_validate()
