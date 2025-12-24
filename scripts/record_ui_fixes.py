"""
Script to record UI fixes in the self-learning system

Records the two issues that were fixed in DataControlCenter.tsx:
1. Property column showing ID instead of name
2. Missing handleRerunAnomalies function implementation
"""

import sys
import os
from datetime import datetime

# Add backend directory to path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

from app.db.database import SessionLocal
from app.services.issue_capture_service import IssueCaptureService
from app.services.self_learning_engine import SelfLearningEngine


def record_issues():
    """Record both UI issues in the self-learning system"""
    db = SessionLocal()
    try:
        capture_service = IssueCaptureService(db)
        learning_engine = SelfLearningEngine(db)

        # Issue 1: Property column showing ID instead of name
        print("Recording Issue 1: Property column display...")
        capture1 = capture_service.capture_error(
            error=None,
            error_message="Property column in Data Control Center Documents tab showing property ID instead of property name",
            issue_category="ui_display_issue",
            severity="error",
            context={
                "component": "DataControlCenter.tsx",
                "tab": "documents",
                "column": "Property",
                "line": 2338,
                "root_cause": "Using doc.property_id directly instead of mapping to property name",
                "symptom": "Users see numeric IDs like '1' instead of readable names like 'ESP Wells Fargo'",
                "user_impact": "Poor UX - users cannot identify properties without referencing IDs"
            }
        )

        if capture1:
            print(f"  ✓ Captured (ID: {capture1.id}, KB ID: {capture1.issue_kb_id})")

            # Record the resolution
            success1 = learning_engine.learn_from_resolution(
                issue_kb_id=capture1.issue_kb_id,
                fix_description="Added getPropertyName() helper function to map property IDs to names. Updated line 2369 to use getPropertyName(doc.property_id) instead of doc.property_id",
                fix_code_location="src/pages/DataControlCenter.tsx:366-370,2369",
                fix_implementation="""
// Helper function added at line 366
const getPropertyName = (propertyId: number): string => {
  const property = properties.find(p => p.id === propertyId);
  return property?.property_name || `Property ${propertyId}`;
};

// Line 2369 changed from:
<td className="py-3 px-4 text-text-secondary">{doc.property_id}</td>

// To:
<td className="py-3 px-4 text-text-secondary">{getPropertyName(doc.property_id)}</td>
"""
            )

            if success1:
                print(f"  ✓ Resolution recorded")
            else:
                print(f"  ✗ Failed to record resolution")
        else:
            print(f"  ✗ Failed to capture issue")

        # Issue 2: Missing handleRerunAnomalies function
        print("\nRecording Issue 2: Missing handleRerunAnomalies function...")
        capture2 = capture_service.capture_error(
            error=None,
            error_message="Re-Run Anomalies button in Documents tab calls non-existent handleRerunAnomalies function",
            issue_category="missing_function",
            severity="critical",
            context={
                "component": "DataControlCenter.tsx",
                "tab": "documents",
                "button": "Re-run Anomalies",
                "line": 2374,
                "root_cause": "Button onClick handler references handleRerunAnomalies() function that was never implemented",
                "symptom": "Runtime error when users click 'Re-run Anomalies' button - function is undefined",
                "user_impact": "Critical feature completely broken - users cannot re-run anomaly detection"
            }
        )

        if capture2:
            print(f"  ✓ Captured (ID: {capture2.id}, KB ID: {capture2.issue_kb_id})")

            # Record the resolution
            success2 = learning_engine.learn_from_resolution(
                issue_kb_id=capture2.issue_kb_id,
                fix_description="Implemented handleRerunAnomalies function that calls the anomaly detection API endpoint, manages loading state, and reloads data after completion",
                fix_code_location="src/pages/DataControlCenter.tsx:619-642",
                fix_implementation="""
// Function added at line 619
const handleRerunAnomalies = async (documentId: number) => {
  try {
    setRerunningAnomalies(documentId);

    const response = await fetch(`${API_BASE_URL}/anomalies/documents/${documentId}/detect`, {
      method: 'POST',
      credentials: 'include'
    });

    if (response.ok) {
      const result = await response.json();
      alert(`Anomaly detection completed successfully. Found ${result.anomalies_detected || 0} anomalies.`);
      loadData(); // Reload the data to reflect new anomaly counts
    } else {
      const error = await response.json();
      alert(`Failed to run anomaly detection: ${error.detail || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Failed to run anomaly detection:', error);
    alert('Failed to run anomaly detection. Please try again.');
  } finally {
    setRerunningAnomalies(null);
  }
};
"""
            )

            if success2:
                print(f"  ✓ Resolution recorded")
            else:
                print(f"  ✗ Failed to record resolution")
        else:
            print(f"  ✗ Failed to capture issue")

        print("\n" + "="*60)
        print("Summary:")
        print("  Issues recorded in self-learning system")
        print("  Future occurrences of similar issues will trigger:")
        print("    - Pre-flight checks to prevent deployment")
        print("    - Automatic detection during code review")
        print("    - Suggested fixes based on previous resolutions")
        print("="*60)

        db.commit()

    except Exception as e:
        print(f"Error recording issues: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    record_issues()
