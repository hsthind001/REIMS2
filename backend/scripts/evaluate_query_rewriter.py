#!/usr/bin/env python3
"""
Evaluate Query Rewriter Recall Improvement

Measures recall improvement from query rewriting on a test set.
Compares recall@k before and after query rewriting.
"""
import sys
import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.query_rewriter_service import QueryRewriterService
from app.services.rag_retrieval_service import RAGRetrievalService
from app.services.fusion_evaluation import FusionEvaluation
from app.db.database import SessionLocal
from app.config.query_rewriter_config import query_rewriter_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_test_queries(file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load test queries with ground truth
    
    Args:
        file_path: Path to JSON file with test queries. If None, uses sample data.
    
    Returns:
        List of test query dictionaries
    """
    if file_path and Path(file_path).exists():
        with open(file_path, 'r') as f:
            return json.load(f)
    
    # Sample test queries (for demonstration)
    return [
        {
            'query_id': 1,
            'query': 'DSCR below 1.25',
            'ground_truth': [1, 4, 7]  # Relevant chunk IDs
        },
        {
            'query_id': 2,
            'query': 'net operating income',
            'ground_truth': [5, 6, 8]
        },
        {
            'query_id': 3,
            'query': 'property revenue',
            'ground_truth': [2, 3, 9]
        }
    ]


def evaluate_recall(
    results: List[Dict[str, Any]],
    ground_truth: List[int],
    top_k: int = 10
) -> Dict[str, float]:
    """
    Evaluate recall metrics
    
    Args:
        results: List of results with 'chunk_id'
        ground_truth: List of relevant chunk IDs
        top_k: Top-k for recall calculation
    
    Returns:
        Dict with recall metrics
    """
    evaluator = FusionEvaluation(top_k=top_k)
    metrics = evaluator.evaluate(results, ground_truth)
    return {
        'recall_at_k': metrics['recall_at_k'],
        'precision_at_k': metrics['precision_at_k'],
        'f1_at_k': metrics['f1_at_k'],
        'ndcg': metrics['ndcg'],
        'relevant_retrieved': metrics['relevant_retrieved'],
        'total_relevant': metrics['total_relevant']
    }


def evaluate_rewriter_improvement(
    test_queries: List[Dict[str, Any]],
    db_session,
    top_k: int = 10
) -> Dict[str, Any]:
    """
    Evaluate recall improvement from query rewriting
    
    Args:
        test_queries: List of test queries with ground truth
        db_session: Database session for RAGRetrievalService
        top_k: Top-k for recall calculation
    
    Returns:
        Dict with evaluation results
    """
    logger.info(f"Evaluating query rewriter improvement on {len(test_queries)} queries (top_k={top_k})")
    
    rewriter = QueryRewriterService()
    rag_service = RAGRetrievalService(db_session)
    
    if not rewriter.use_openai and len(rewriter.synonym_dict) == 0:
        logger.error("No rewriting method available. Cannot evaluate.")
        return {
            'error': 'No rewriting method available',
            'rewriter_status': rewriter.get_status()
        }
    
    initial_recalls = []
    rewritten_recalls = []
    query_results = []
    
    for test_query in test_queries:
        query = test_query['query']
        ground_truth = test_query['ground_truth']
        
        # Search without rewriting
        try:
            initial_results = rag_service.retrieve_relevant_chunks(
                query=query,
                top_k=top_k,
                use_query_rewriting=False
            )
            
            # Evaluate initial results
            initial_metrics = evaluate_recall(initial_results, ground_truth, top_k)
            initial_recall = initial_metrics['recall_at_k']
            initial_recalls.append(initial_recall)
        except Exception as e:
            logger.error(f"Error retrieving initial results for query {test_query.get('query_id')}: {e}", exc_info=True)
            initial_recall = 0.0
            initial_recalls.append(initial_recall)
            initial_metrics = {'recall_at_k': 0.0, 'precision_at_k': 0.0, 'f1_at_k': 0.0, 'ndcg': 0.0}
        
        # Search with rewriting
        try:
            rewritten_results = rag_service.retrieve_relevant_chunks(
                query=query,
                top_k=top_k,
                use_query_rewriting=True
            )
            
            # Evaluate rewritten results
            rewritten_metrics = evaluate_recall(rewritten_results, ground_truth, top_k)
            rewritten_recall = rewritten_metrics['recall_at_k']
            rewritten_recalls.append(rewritten_recall)
            
            improvement = rewritten_recall - initial_recall
            improvement_pct = (improvement / initial_recall * 100) if initial_recall > 0 else 0
            
            query_results.append({
                'query_id': test_query.get('query_id'),
                'query': query,
                'initial_recall': initial_recall,
                'rewritten_recall': rewritten_recall,
                'improvement': improvement,
                'improvement_pct': improvement_pct,
                'initial_metrics': initial_metrics,
                'rewritten_metrics': rewritten_metrics
            })
            
            logger.info(
                f"Query {test_query.get('query_id')}: "
                f"Initial recall={initial_recall:.4f}, "
                f"Rewritten recall={rewritten_recall:.4f}, "
                f"Improvement={improvement:+.4f} ({improvement_pct:+.2f}%)"
            )
            
        except Exception as e:
            logger.error(f"Error retrieving rewritten results for query {test_query.get('query_id')}: {e}", exc_info=True)
            rewritten_recalls.append(initial_recall)  # Use initial if rewritten fails
            query_results.append({
                'query_id': test_query.get('query_id'),
                'query': query,
                'initial_recall': initial_recall,
                'rewritten_recall': initial_recall,
                'improvement': 0.0,
                'error': str(e)
            })
    
    # Calculate averages
    avg_initial_recall = sum(initial_recalls) / len(initial_recalls) if initial_recalls else 0.0
    avg_rewritten_recall = sum(rewritten_recalls) / len(rewritten_recalls) if rewritten_recalls else 0.0
    avg_improvement = avg_rewritten_recall - avg_initial_recall
    avg_improvement_pct = (avg_improvement / avg_initial_recall * 100) if avg_initial_recall > 0 else 0
    
    logger.info("=" * 60)
    logger.info("Evaluation Summary")
    logger.info("=" * 60)
    logger.info(f"Average Initial Recall@{top_k}: {avg_initial_recall:.4f}")
    logger.info(f"Average Rewritten Recall@{top_k}: {avg_rewritten_recall:.4f}")
    logger.info(f"Average Improvement: {avg_improvement:+.4f} ({avg_improvement_pct:+.2f}%)")
    logger.info(f"Target Improvement (15%+): {'✅ MET' if avg_improvement_pct >= 15 else '❌ NOT MET'}")
    logger.info("=" * 60)
    
    return {
        'avg_initial_recall': avg_initial_recall,
        'avg_rewritten_recall': avg_rewritten_recall,
        'avg_improvement': avg_improvement,
        'avg_improvement_pct': avg_improvement_pct,
        'target_improvement_pct': 15.0,
        'target_met': avg_improvement_pct >= 15.0,
        'query_results': query_results,
        'rewriter_status': rewriter.get_status()
    }


def main():
    """Main function for evaluation"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Evaluate query rewriter recall improvement')
    parser.add_argument('--test-queries', type=str, help='Path to JSON file with test queries')
    parser.add_argument('--top-k', type=int, default=10, help='Top-k for recall calculation')
    parser.add_argument('--output', type=str, help='Output file for results (JSON)')
    
    args = parser.parse_args()
    
    # Load test queries
    test_queries = load_test_queries(args.test_queries)
    logger.info(f"Loaded {len(test_queries)} test queries")
    
    # Create database session
    db = SessionLocal()
    try:
        # Evaluate
        results = evaluate_rewriter_improvement(test_queries, db, top_k=args.top_k)
        
        # Print summary
        print(f"\n{'='*60}")
        print("Query Rewriter Evaluation Results")
        print(f"{'='*60}")
        print(f"Average Initial Recall@{args.top_k}: {results.get('avg_initial_recall', 0):.4f}")
        print(f"Average Rewritten Recall@{args.top_k}: {results.get('avg_rewritten_recall', 0):.4f}")
        print(f"Average Improvement: {results.get('avg_improvement', 0):+.4f} ({results.get('avg_improvement_pct', 0):+.2f}%)")
        print(f"Target Improvement (15%+): {'✅ MET' if results.get('target_met') else '❌ NOT MET'}")
        print(f"{'='*60}")
        
        # Save results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {args.output}")
        
        return 0 if results.get('target_met', False) else 1
        
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())

