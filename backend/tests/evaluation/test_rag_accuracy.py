"""
RAG Accuracy Evaluation Script

Tests retrieval accuracy with ground truth data.
Measures precision@k, recall@k, and identifies issues.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.rag_retrieval_service import RAGRetrievalService
from app.services.rag_retrieval_service_fixed import FixedRAGRetrievalService
from app.services.rag_accuracy_diagnostics import RAGAccuracyDiagnostics
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGAccuracyEvaluator:
    """
    Evaluate RAG retrieval accuracy.
    
    Tests:
    - Precision@k
    - Recall@k
    - Metadata filtering accuracy
    - Hybrid vs semantic comparison
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.old_service = RAGRetrievalService(db)
        self.new_service = FixedRAGRetrievalService(db)
        self.diagnostics = RAGAccuracyDiagnostics()
    
    def evaluate_query(
        self,
        query: str,
        ground_truth_chunk_ids: List[int],
        expected_property_id: Optional[int] = None,
        expected_period_id: Optional[int] = None,
        expected_document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a single query.
        
        Args:
            query: Query text
            ground_truth_chunk_ids: List of relevant chunk IDs
            expected_property_id: Expected property ID
            expected_period_id: Expected period ID
            expected_document_type: Expected document type
        
        Returns:
            Evaluation results
        """
        results = {
            'query': query,
            'ground_truth_count': len(ground_truth_chunk_ids),
            'methods': {}
        }
        
        # Test semantic-only
        semantic_results = self.old_service.retrieve_relevant_chunks(
            query=query,
            top_k=10,
            property_id=expected_property_id,
            period_id=expected_period_id,
            document_type=expected_document_type,
            use_bm25=False,
            use_rrf=False
        )
        
        results['methods']['semantic'] = self._calculate_metrics(
            semantic_results, ground_truth_chunk_ids
        )
        
        # Test BM25-only
        if self.old_service.bm25_service:
            bm25_results = self.old_service.retrieve_relevant_chunks(
                query=query,
                top_k=10,
                property_id=expected_property_id,
                period_id=expected_period_id,
                document_type=expected_document_type,
                use_bm25=True,
                use_rrf=False
            )
            
            results['methods']['bm25'] = self._calculate_metrics(
                bm25_results, ground_truth_chunk_ids
            )
        
        # Test hybrid (old)
        hybrid_results_old = self.old_service.retrieve_relevant_chunks(
            query=query,
            top_k=10,
            property_id=expected_property_id,
            period_id=expected_period_id,
            document_type=expected_document_type,
            use_bm25=True,
            use_rrf=True,
            rrf_alpha=0.7
        )
        
        results['methods']['hybrid_old'] = self._calculate_metrics(
            hybrid_results_old, ground_truth_chunk_ids
        )
        
        # Test fixed service
        fixed_results = self.new_service.retrieve_relevant_chunks(
            query=query,
            top_k=10,
            property_id=expected_property_id,
            period_id=expected_period_id,
            document_type=expected_document_type,
            use_bm25=True,
            use_rrf=True
        )
        
        results['methods']['hybrid_fixed'] = self._calculate_metrics(
            fixed_results, ground_truth_chunk_ids
        )
        
        # Diagnose issues
        results['diagnostics'] = self.diagnostics.diagnose_hybrid_degradation(
            semantic_results=semantic_results,
            bm25_results=bm25_results if self.old_service.bm25_service else [],
            fused_results=hybrid_results_old,
            ground_truth=ground_truth_chunk_ids
        )
        
        results['metadata_diagnostics'] = self.diagnostics.diagnose_metadata_filtering(
            query=query,
            results=hybrid_results_old,
            expected_property_id=expected_property_id,
            expected_period_id=expected_period_id,
            expected_document_type=expected_document_type
        )
        
        return results
    
    def _calculate_metrics(
        self,
        results: List[Dict],
        ground_truth: List[int],
        k_values: List[int] = [1, 3, 5, 10]
    ) -> Dict[str, float]:
        """Calculate precision@k and recall@k."""
        metrics = {}
        
        result_chunk_ids = [r.get('chunk_id') for r in results]
        
        for k in k_values:
            top_k_ids = result_chunk_ids[:k]
            relevant_in_top_k = set(top_k_ids) & set(ground_truth)
            
            precision = len(relevant_in_top_k) / k if k > 0 else 0.0
            recall = len(relevant_in_top_k) / len(ground_truth) if ground_truth else 0.0
            
            metrics[f'precision@{k}'] = precision
            metrics[f'recall@{k}'] = recall
        
        return metrics
    
    def run_evaluation_suite(self) -> Dict[str, Any]:
        """
        Run evaluation suite with test queries.
        
        Returns:
            Comprehensive evaluation results
        """
        test_cases = [
            {
                'query': 'What was NOI for Eastern Shore in Q3 2024?',
                'ground_truth': [],  # TODO: Fill with actual chunk IDs
                'expected_property_id': 1,  # TODO: Get from database
                'expected_period_id': 1,  # TODO: Get Q3 2024 period_id
                'expected_document_type': 'income_statement'
            },
            {
                'query': 'Show me properties with losses',
                'ground_truth': [],  # TODO: Fill with actual chunk IDs
                'expected_document_type': 'income_statement'
            }
        ]
        
        all_results = []
        for test_case in test_cases:
            logger.info(f"Evaluating query: {test_case['query']}")
            result = self.evaluate_query(**test_case)
            all_results.append(result)
        
        # Aggregate results
        summary = self._aggregate_results(all_results)
        
        return {
            'test_cases': all_results,
            'summary': summary,
            'recommendations': self._generate_recommendations(all_results)
        }
    
    def _aggregate_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Aggregate results across all test cases."""
        methods = ['semantic', 'bm25', 'hybrid_old', 'hybrid_fixed']
        aggregated = {method: {'precision@5': [], 'precision@10': []} for method in methods}
        
        for result in results:
            for method in methods:
                if method in result['methods']:
                    metrics = result['methods'][method]
                    aggregated[method]['precision@5'].append(metrics.get('precision@5', 0))
                    aggregated[method]['precision@10'].append(metrics.get('precision@10', 0))
        
        # Calculate averages
        summary = {}
        for method, values in aggregated.items():
            if values['precision@5']:
                summary[method] = {
                    'avg_precision@5': sum(values['precision@5']) / len(values['precision@5']),
                    'avg_precision@10': sum(values['precision@10']) / len(values['precision@10'])
                }
        
        return summary
    
    def _generate_recommendations(self, results: List[Dict]) -> List[Dict]:
        """Generate recommendations based on evaluation results."""
        recommendations = []
        
        for result in results:
            diagnostics = result.get('diagnostics', {})
            for issue in diagnostics.get('issues', []):
                if issue['severity'] == 'high':
                    recommendations.append({
                        'priority': 'HIGH',
                        'issue': issue['description'],
                        'fix': issue.get('recommendation', 'See diagnostics')
                    })
        
        return recommendations


def main():
    """Run evaluation."""
    # Initialize database
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        evaluator = RAGAccuracyEvaluator(db)
        results = evaluator.run_evaluation_suite()
        
        # Print results
        print("\n" + "="*80)
        print("RAG ACCURACY EVALUATION RESULTS")
        print("="*80)
        
        print("\nSummary:")
        for method, metrics in results['summary'].items():
            print(f"\n{method}:")
            print(f"  Precision@5: {metrics['avg_precision@5']:.2%}")
            print(f"  Precision@10: {metrics['avg_precision@10']:.2%}")
        
        print("\nRecommendations:")
        for rec in results['recommendations']:
            print(f"\n[{rec['priority']}] {rec['issue']}")
            print(f"  Fix: {rec['fix']}")
        
        # Save to file
        import json
        with open('rag_accuracy_evaluation.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print("\nDetailed results saved to: rag_accuracy_evaluation.json")
        
    finally:
        db.close()


if __name__ == '__main__':
    main()

