#!/usr/bin/env python3
"""
Hallucination Detection Accuracy Measurement Script

Measures accuracy of hallucination detection on a test set.
Calculates true positives, false positives, false negatives, and hallucination rate.
"""
import sys
import os
import logging
from typing import List, Dict, Any, Optional

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.hallucination_detector import HallucinationDetector
from app.config.hallucination_config import hallucination_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestCase:
    """Represents a test case for hallucination detection"""
    
    def __init__(
        self,
        answer: str,
        has_hallucination: bool,
        expected_claims: List[Dict[str, Any]],
        property_id: Optional[int] = None,
        period_id: Optional[int] = None,
        sources: Optional[List[Dict[str, Any]]] = None
    ):
        self.answer = answer
        self.has_hallucination = has_hallucination
        self.expected_claims = expected_claims
        self.property_id = property_id
        self.period_id = period_id
        self.sources = sources or []


def create_test_cases() -> List[TestCase]:
    """
    Create test cases for hallucination detection
    
    Returns:
        List of test cases
    """
    test_cases = []
    
    # Test Case 1: Correct NOI (no hallucination)
    test_cases.append(TestCase(
        answer="The NOI was $1,200,000 for the property in Q3 2024.",
        has_hallucination=False,
        expected_claims=[
            {'type': 'currency', 'value': 1200000.0, 'verified': True}
        ],
        property_id=1,
        period_id=1
    ))
    
    # Test Case 2: Wrong NOI (hallucination)
    test_cases.append(TestCase(
        answer="The NOI was $1,500,000 for the property in Q3 2024.",
        has_hallucination=True,
        expected_claims=[
            {'type': 'currency', 'value': 1500000.0, 'verified': False}
        ],
        property_id=1,
        period_id=1
    ))
    
    # Test Case 3: Correct DSCR (no hallucination)
    test_cases.append(TestCase(
        answer="The DSCR was 1.25 for the property.",
        has_hallucination=False,
        expected_claims=[
            {'type': 'ratio', 'value': 1.25, 'verified': True}
        ],
        property_id=1,
        period_id=1
    ))
    
    # Test Case 4: Wrong DSCR (hallucination)
    test_cases.append(TestCase(
        answer="The DSCR was 1.5 for the property.",
        has_hallucination=True,
        expected_claims=[
            {'type': 'ratio', 'value': 1.5, 'verified': False}
        ],
        property_id=1,
        period_id=1
    ))
    
    # Test Case 5: Correct occupancy (no hallucination)
    test_cases.append(TestCase(
        answer="The occupancy rate was 85% last month.",
        has_hallucination=False,
        expected_claims=[
            {'type': 'percentage', 'value': 85.0, 'verified': True}
        ],
        property_id=1,
        period_id=1
    ))
    
    # Test Case 6: Wrong occupancy (hallucination)
    test_cases.append(TestCase(
        answer="The occupancy rate was 95% last month.",
        has_hallucination=True,
        expected_claims=[
            {'type': 'percentage', 'value': 95.0, 'verified': False}
        ],
        property_id=1,
        period_id=1
    ))
    
    # Test Case 7: Multiple claims, one wrong (hallucination)
    test_cases.append(TestCase(
        answer="The NOI was $1.2M with 85% occupancy and DSCR of 1.5.",
        has_hallucination=True,
        expected_claims=[
            {'type': 'currency', 'value': 1200000.0, 'verified': True},
            {'type': 'percentage', 'value': 85.0, 'verified': True},
            {'type': 'ratio', 'value': 1.5, 'verified': False}
        ],
        property_id=1,
        period_id=1
    ))
    
    # Test Case 8: Verified against documents (no hallucination)
    test_cases.append(TestCase(
        answer="The NOI was $1.2M according to the income statement.",
        has_hallucination=False,
        expected_claims=[
            {'type': 'currency', 'value': 1200000.0, 'verified': True}
        ],
        sources=[
            {'chunk_text': 'Net Operating Income: $1,200,000', 'chunk_id': 1}
        ]
    ))
    
    return test_cases


def measure_accuracy(db: Session) -> Dict[str, Any]:
    """
    Measure hallucination detection accuracy on test set
    
    Args:
        db: Database session
    
    Returns:
        Dict with accuracy metrics
    """
    detector = HallucinationDetector(db)
    test_cases = create_test_cases()
    
    true_positives = 0  # Correctly detected hallucinations
    false_positives = 0  # Incorrectly flagged as hallucinations
    false_negatives = 0  # Missed hallucinations
    true_negatives = 0  # Correctly identified as no hallucinations
    
    total_claims = 0
    verified_claims = 0
    unverified_claims = 0
    
    for test_case in test_cases:
        result = detector.detect_hallucinations(
            answer=test_case.answer,
            sources=test_case.sources,
            property_id=test_case.property_id,
            period_id=test_case.period_id
        )
        
        detected_hallucination = result.get('has_hallucinations', False)
        expected_hallucination = test_case.has_hallucination
        
        # Calculate metrics
        if expected_hallucination and detected_hallucination:
            true_positives += 1
        elif expected_hallucination and not detected_hallucination:
            false_negatives += 1
        elif not expected_hallucination and detected_hallucination:
            false_positives += 1
        else:
            true_negatives += 1
        
        # Track claims
        total_claims += result.get('total_claims', 0)
        verified_claims += result.get('verified_claims', 0)
        unverified_claims += result.get('unverified_claims', 0)
    
    # Calculate metrics
    total_cases = len(test_cases)
    accuracy = (true_positives + true_negatives) / total_cases if total_cases > 0 else 0.0
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    hallucination_rate = unverified_claims / total_claims if total_claims > 0 else 0.0
    
    return {
        'total_cases': total_cases,
        'true_positives': true_positives,
        'false_positives': false_positives,
        'false_negatives': false_negatives,
        'true_negatives': true_negatives,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'total_claims': total_claims,
        'verified_claims': verified_claims,
        'unverified_claims': unverified_claims,
        'hallucination_rate': hallucination_rate,
        'target_hallucination_rate': hallucination_config.TARGET_HALLUCINATION_RATE,
        'meets_target': hallucination_rate < hallucination_config.TARGET_HALLUCINATION_RATE
    }


def main():
    """Main function"""
    logger.info("Starting hallucination detection accuracy measurement...")
    
    db = SessionLocal()
    
    try:
        metrics = measure_accuracy(db)
        
        logger.info("\n" + "="*60)
        logger.info("Hallucination Detection Accuracy Report")
        logger.info("="*60)
        logger.info(f"\nTotal Test Cases: {metrics['total_cases']}")
        logger.info(f"\nConfusion Matrix:")
        logger.info(f"  True Positives (TP):  {metrics['true_positives']}")
        logger.info(f"  False Positives (FP): {metrics['false_positives']}")
        logger.info(f"  False Negatives (FN): {metrics['false_negatives']}")
        logger.info(f"  True Negatives (TN): {metrics['true_negatives']}")
        logger.info(f"\nMetrics:")
        logger.info(f"  Accuracy:  {metrics['accuracy']:.2%}")
        logger.info(f"  Precision: {metrics['precision']:.2%}")
        logger.info(f"  Recall:    {metrics['recall']:.2%}")
        logger.info(f"  F1 Score:  {metrics['f1_score']:.2%}")
        logger.info(f"\nClaims:")
        logger.info(f"  Total Claims:     {metrics['total_claims']}")
        logger.info(f"  Verified Claims:  {metrics['verified_claims']}")
        logger.info(f"  Unverified Claims: {metrics['unverified_claims']}")
        logger.info(f"  Hallucination Rate: {metrics['hallucination_rate']:.2%}")
        logger.info(f"  Target Rate:      {metrics['target_hallucination_rate']:.2%}")
        logger.info(f"  Meets Target:     {'✅ YES' if metrics['meets_target'] else '❌ NO'}")
        logger.info("="*60)
        
        # Return exit code based on whether target is met
        return 0 if metrics['meets_target'] else 1
        
    except Exception as e:
        logger.error(f"Accuracy measurement failed: {e}", exc_info=True)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())

