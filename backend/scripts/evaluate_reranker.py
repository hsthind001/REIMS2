#!/usr/bin/env python3
"""
Evaluate Reranker Precision Improvement

Measures precision improvement from reranking on a test set.
Compares precision@5 before and after reranking.
"""
import sys
import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.reranker_service import RerankerService
from app.services.fusion_evaluation import FusionEvaluation
from app.config.reranker_config import reranker_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_test_queries(file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load test queries with initial results and ground truth
    
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
            'initial_results': [
                {'chunk_id': 1, 'chunk_text': 'DSCR is 1.20, below threshold', 'similarity': 0.9},
                {'chunk_id': 2, 'chunk_text': 'Debt service coverage analysis', 'similarity': 0.85},
                {'chunk_id': 3, 'chunk_text': 'Financial metrics discussion', 'similarity': 0.8},
                {'chunk_id': 4, 'chunk_text': 'DSCR calculation shows 1.15', 'similarity': 0.75},
                {'chunk_id': 5, 'chunk_text': 'General financial data', 'similarity': 0.7},
            ],
            'ground_truth': [1, 4]  # Relevant chunk IDs
        },
        {
            'query_id': 2,
            'query': 'net operating income',
            'initial_results': [
                {'chunk_id': 6, 'chunk_text': 'Net operating income increased', 'similarity': 0.95},
                {'chunk_id': 7, 'chunk_text': 'NOI calculation details', 'similarity': 0.9},
                {'chunk_id': 8, 'chunk_text': 'Operating income analysis', 'similarity': 0.85},
                {'chunk_id': 9, 'chunk_text': 'Income statement data', 'similarity': 0.8},
                {'chunk_id': 10, 'chunk_text': 'General revenue information', 'similarity': 0.75},
            ],
            'ground_truth': [6, 7]
        }
    ]


def evaluate_precision(
    results: List[Dict[str, Any]],
    ground_truth: List[int],
    top_k: int = 5
) -> Dict[str, float]:
    """
    Evaluate precision metrics
    
    Args:
        results: List of results with 'chunk_id'
        ground_truth: List of relevant chunk IDs
        top_k: Top-k for precision calculation
    
    Returns:
        Dict with precision metrics
    """
    evaluator = FusionEvaluation(top_k=top_k)
    metrics = evaluator.evaluate(results, ground_truth)
    return {
        'precision_at_k': metrics['precision_at_k'],
        'recall_at_k': metrics['recall_at_k'],
        'f1_at_k': metrics['f1_at_k'],
        'ndcg': metrics['ndcg'],
        'mrr': metrics['mrr']
    }


def evaluate_reranker_improvement(
    test_queries: List[Dict[str, Any]],
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Evaluate precision improvement from reranking
    
    Args:
        test_queries: List of test queries with initial results and ground truth
        top_k: Top-k for precision calculation
    
    Returns:
        Dict with evaluation results
    """
    logger.info(f"Evaluating reranker improvement on {len(test_queries)} queries (top_k={top_k})")
    
    reranker = RerankerService()
    
    if not reranker.use_cohere and not reranker.use_fallback:
        logger.error("No reranking method available. Cannot evaluate.")
        return {
            'error': 'No reranking method available',
            'reranker_status': reranker.get_status()
        }
    
    initial_precisions = []
    reranked_precisions = []
    query_results = []
    
    for test_query in test_queries:
        query = test_query['query']
        initial_results = test_query['initial_results']
        ground_truth = test_query['ground_truth']
        
        # Evaluate initial results
        initial_metrics = evaluate_precision(initial_results[:top_k], ground_truth, top_k)
        initial_precision = initial_metrics['precision_at_k']
        initial_precisions.append(initial_precision)
        
        # Rerank results
        try:
            reranked_results = reranker.rerank(
                query=query,
                candidates=initial_results,
                top_k=top_k
            )
            
            # Evaluate reranked results
            reranked_metrics = evaluate_precision(reranked_results, ground_truth, top_k)
            reranked_precision = reranked_metrics['precision_at_k']
            reranked_precisions.append(reranked_precision)
            
            improvement = reranked_precision - initial_precision
            
            query_results.append({
                'query_id': test_query.get('query_id'),
                'query': query,
                'initial_precision': initial_precision,
                'reranked_precision': reranked_precision,
                'improvement': improvement,
                'improvement_pct': (improvement / initial_precision * 100) if initial_precision > 0 else 0,
                'initial_metrics': initial_metrics,
                'reranked_metrics': reranked_metrics
            })
            
            logger.info(
                f"Query {test_query.get('query_id')}: "
                f"Initial precision={initial_precision:.4f}, "
                f"Reranked precision={reranked_precision:.4f}, "
                f"Improvement={improvement:+.4f}"
            )
            
        except Exception as e:
            logger.error(f"Error reranking query {test_query.get('query_id')}: {e}", exc_info=True)
            # Use initial precision if reranking fails
            reranked_precisions.append(initial_precision)
            query_results.append({
                'query_id': test_query.get('query_id'),
                'query': query,
                'initial_precision': initial_precision,
                'reranked_precision': initial_precision,
                'improvement': 0.0,
                'error': str(e)
            })
    
    # Calculate averages
    avg_initial_precision = sum(initial_precisions) / len(initial_precisions) if initial_precisions else 0.0
    avg_reranked_precision = sum(reranked_precisions) / len(reranked_precisions) if reranked_precisions else 0.0
    avg_improvement = avg_reranked_precision - avg_initial_precision
    avg_improvement_pct = (avg_improvement / avg_initial_precision * 100) if avg_initial_precision > 0 else 0
    
    logger.info("=" * 60)
    logger.info("Evaluation Summary")
    logger.info("=" * 60)
    logger.info(f"Average Initial Precision@{top_k}: {avg_initial_precision:.4f}")
    logger.info(f"Average Reranked Precision@{top_k}: {avg_reranked_precision:.4f}")
    logger.info(f"Average Improvement: {avg_improvement:+.4f} ({avg_improvement_pct:+.2f}%)")
    logger.info("=" * 60)
    
    return {
        'avg_initial_precision': avg_initial_precision,
        'avg_reranked_precision': avg_reranked_precision,
        'avg_improvement': avg_improvement,
        'avg_improvement_pct': avg_improvement_pct,
        'target_precision': 0.90,
        'target_met': avg_reranked_precision >= 0.90,
        'query_results': query_results,
        'reranker_status': reranker.get_status()
    }


def main():
    """Main function for evaluation"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Evaluate reranker precision improvement')
    parser.add_argument('--test-queries', type=str, help='Path to JSON file with test queries')
    parser.add_argument('--top-k', type=int, default=5, help='Top-k for precision calculation')
    parser.add_argument('--output', type=str, help='Output file for results (JSON)')
    
    args = parser.parse_args()
    
    # Load test queries
    test_queries = load_test_queries(args.test_queries)
    logger.info(f"Loaded {len(test_queries)} test queries")
    
    # Evaluate
    results = evaluate_reranker_improvement(test_queries, top_k=args.top_k)
    
    # Print summary
    print(f"\n{'='*60}")
    print("Reranker Evaluation Results")
    print(f"{'='*60}")
    print(f"Average Initial Precision@{args.top_k}: {results.get('avg_initial_precision', 0):.4f}")
    print(f"Average Reranked Precision@{args.top_k}: {results.get('avg_reranked_precision', 0):.4f}")
    print(f"Average Improvement: {results.get('avg_improvement', 0):+.4f} ({results.get('avg_improvement_pct', 0):+.2f}%)")
    print(f"Target Precision (90%): {'✅ MET' if results.get('target_met') else '❌ NOT MET'}")
    print(f"{'='*60}")
    
    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {args.output}")
    
    return 0 if results.get('target_met', False) else 1


if __name__ == "__main__":
    sys.exit(main())

