#!/usr/bin/env python3
"""
Tune Fusion Parameters Script

Evaluates different alpha and k values to find optimal fusion parameters.
Tests fusion performance across multiple queries with ground truth.
"""
import sys
import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.fusion_service import FusionService
from app.services.fusion_evaluation import FusionEvaluation
from app.config.fusion_config import fusion_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_test_queries(file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load test queries with semantic and keyword results
    
    Args:
        file_path: Path to JSON file with test queries. If None, uses sample data.
    
    Returns:
        List of test query dictionaries
    """
    if file_path and Path(file_path).exists():
        with open(file_path, 'r') as f:
            return json.load(f)
    
    # Sample test queries (for demonstration)
    # In production, load from actual query logs or evaluation dataset
    return [
        {
            'query_id': 1,
            'query': 'DSCR below 1.25',
            'semantic_results': [
                {'chunk_id': 1, 'similarity': 0.9, 'chunk_text': 'DSCR is 1.20, below threshold'},
                {'chunk_id': 2, 'similarity': 0.8, 'chunk_text': 'Debt service coverage ratio analysis'},
                {'chunk_id': 3, 'similarity': 0.7, 'chunk_text': 'Financial metrics discussion'},
            ],
            'keyword_results': [
                {'chunk_id': 1, 'score': 2.5, 'chunk_text': 'DSCR is 1.20, below threshold'},
                {'chunk_id': 4, 'score': 2.0, 'chunk_text': 'DSCR calculation shows 1.15'},
                {'chunk_id': 2, 'score': 1.8, 'chunk_text': 'Debt service coverage ratio analysis'},
            ],
            'ground_truth': [1, 4]  # Relevant chunk IDs
        },
        {
            'query_id': 2,
            'query': 'net operating income',
            'semantic_results': [
                {'chunk_id': 5, 'similarity': 0.95, 'chunk_text': 'Net operating income increased'},
                {'chunk_id': 6, 'similarity': 0.85, 'chunk_text': 'NOI calculation details'},
            ],
            'keyword_results': [
                {'chunk_id': 5, 'score': 2.8, 'chunk_text': 'Net operating income increased'},
                {'chunk_id': 7, 'score': 2.2, 'chunk_text': 'Operating income analysis'},
            ],
            'ground_truth': [5, 6]
        }
    ]


def tune_alpha(
    test_queries: List[Dict[str, Any]],
    k: int = 60,
    alpha_min: float = 0.0,
    alpha_max: float = 1.0,
    alpha_step: float = 0.1
) -> Dict[str, Any]:
    """
    Tune alpha parameter across multiple queries
    
    Args:
        test_queries: List of test queries with results and ground truth
        k: Fixed k value for RRF
        alpha_min: Minimum alpha to test
        alpha_max: Maximum alpha to test
        alpha_step: Step size for alpha
    
    Returns:
        Dict with best alpha and evaluation results
    """
    logger.info(f"Tuning alpha parameter (k={k}, range=[{alpha_min}, {alpha_max}], step={alpha_step})")
    
    evaluator = FusionEvaluation(top_k=20)
    best_alpha = None
    best_avg_precision = 0.0
    alpha_results = []
    
    current_alpha = alpha_min
    while current_alpha <= alpha_max:
        logger.info(f"Testing alpha={current_alpha:.2f}")
        
        fusion_service = FusionService(alpha=current_alpha, k=k)
        query_metrics = []
        
        for test_query in test_queries:
            # Fuse results
            fused = fusion_service.fuse(
                semantic_results=test_query['semantic_results'],
                keyword_results=test_query['keyword_results'],
                top_k=20
            )
            
            # Evaluate
            metrics = evaluator.evaluate(fused, test_query['ground_truth'])
            query_metrics.append(metrics)
        
        # Calculate average metrics
        avg_precision = sum(m['precision_at_k'] for m in query_metrics) / len(query_metrics)
        avg_recall = sum(m['recall_at_k'] for m in query_metrics) / len(query_metrics)
        avg_f1 = sum(m['f1_at_k'] for m in query_metrics) / len(query_metrics)
        avg_ndcg = sum(m['ndcg'] for m in query_metrics) / len(query_metrics)
        
        alpha_results.append({
            'alpha': round(current_alpha, 2),
            'avg_precision_at_k': avg_precision,
            'avg_recall_at_k': avg_recall,
            'avg_f1_at_k': avg_f1,
            'avg_ndcg': avg_ndcg,
            'query_metrics': query_metrics
        })
        
        if avg_precision > best_avg_precision:
            best_avg_precision = avg_precision
            best_alpha = round(current_alpha, 2)
        
        current_alpha += alpha_step
        current_alpha = round(current_alpha, 2)
    
    logger.info(f"Best alpha: {best_alpha} (avg precision: {best_avg_precision:.4f})")
    
    return {
        'best_alpha': best_alpha,
        'best_avg_precision': best_avg_precision,
        'k': k,
        'alpha_results': alpha_results
    }


def tune_k(
    test_queries: List[Dict[str, Any]],
    alpha: float = 0.7,
    k_min: int = 30,
    k_max: int = 100,
    k_step: int = 10
) -> Dict[str, Any]:
    """
    Tune k parameter across multiple queries
    
    Args:
        test_queries: List of test queries with results and ground truth
        alpha: Fixed alpha value for RRF
        k_min: Minimum k to test
        k_max: Maximum k to test
        k_step: Step size for k
    
    Returns:
        Dict with best k and evaluation results
    """
    logger.info(f"Tuning k parameter (alpha={alpha}, range=[{k_min}, {k_max}], step={k_step})")
    
    evaluator = FusionEvaluation(top_k=20)
    best_k = None
    best_avg_precision = 0.0
    k_results = []
    
    current_k = k_min
    while current_k <= k_max:
        logger.info(f"Testing k={current_k}")
        
        fusion_service = FusionService(alpha=alpha, k=current_k)
        query_metrics = []
        
        for test_query in test_queries:
            # Fuse results
            fused = fusion_service.fuse(
                semantic_results=test_query['semantic_results'],
                keyword_results=test_query['keyword_results'],
                top_k=20
            )
            
            # Evaluate
            metrics = evaluator.evaluate(fused, test_query['ground_truth'])
            query_metrics.append(metrics)
        
        # Calculate average metrics
        avg_precision = sum(m['precision_at_k'] for m in query_metrics) / len(query_metrics)
        avg_recall = sum(m['recall_at_k'] for m in query_metrics) / len(query_metrics)
        avg_f1 = sum(m['f1_at_k'] for m in query_metrics) / len(query_metrics)
        avg_ndcg = sum(m['ndcg'] for m in query_metrics) / len(query_metrics)
        
        k_results.append({
            'k': current_k,
            'avg_precision_at_k': avg_precision,
            'avg_recall_at_k': avg_recall,
            'avg_f1_at_k': avg_f1,
            'avg_ndcg': avg_ndcg,
            'query_metrics': query_metrics
        })
        
        if avg_precision > best_avg_precision:
            best_avg_precision = avg_precision
            best_k = current_k
        
        current_k += k_step
    
    logger.info(f"Best k: {best_k} (avg precision: {best_avg_precision:.4f})")
    
    return {
        'best_k': best_k,
        'best_avg_precision': best_avg_precision,
        'alpha': alpha,
        'k_results': k_results
    }


def tune_both(
    test_queries: List[Dict[str, Any]],
    alpha_range: Tuple[float, float] = (0.0, 1.0),
    alpha_step: float = 0.2,
    k_range: Tuple[int, int] = (30, 100),
    k_step: int = 20
) -> Dict[str, Any]:
    """
    Tune both alpha and k parameters (grid search)
    
    Args:
        test_queries: List of test queries with results and ground truth
        alpha_range: Range of alpha values to test
        alpha_step: Step size for alpha
        k_range: Range of k values to test
        k_step: Step size for k
    
    Returns:
        Dict with best parameters and evaluation results
    """
    logger.info(f"Tuning both alpha and k (grid search)")
    
    evaluator = FusionEvaluation(top_k=20)
    best_alpha = None
    best_k = None
    best_avg_precision = 0.0
    grid_results = []
    
    alpha_min, alpha_max = alpha_range
    k_min, k_max = k_range
    
    current_alpha = alpha_min
    while current_alpha <= alpha_max:
        current_k = k_min
        while current_k <= k_max:
            logger.info(f"Testing alpha={current_alpha:.2f}, k={current_k}")
            
            fusion_service = FusionService(alpha=current_alpha, k=current_k)
            query_metrics = []
            
            for test_query in test_queries:
                # Fuse results
                fused = fusion_service.fuse(
                    semantic_results=test_query['semantic_results'],
                    keyword_results=test_query['keyword_results'],
                    top_k=20
                )
                
                # Evaluate
                metrics = evaluator.evaluate(fused, test_query['ground_truth'])
                query_metrics.append(metrics)
            
            # Calculate average metrics
            avg_precision = sum(m['precision_at_k'] for m in query_metrics) / len(query_metrics)
            avg_recall = sum(m['recall_at_k'] for m in query_metrics) / len(query_metrics)
            avg_f1 = sum(m['f1_at_k'] for m in query_metrics) / len(query_metrics)
            avg_ndcg = sum(m['ndcg'] for m in query_metrics) / len(query_metrics)
            
            grid_results.append({
                'alpha': round(current_alpha, 2),
                'k': current_k,
                'avg_precision_at_k': avg_precision,
                'avg_recall_at_k': avg_recall,
                'avg_f1_at_k': avg_f1,
                'avg_ndcg': avg_ndcg
            })
            
            if avg_precision > best_avg_precision:
                best_avg_precision = avg_precision
                best_alpha = round(current_alpha, 2)
                best_k = current_k
            
            current_k += k_step
        
        current_alpha += alpha_step
        current_alpha = round(current_alpha, 2)
    
    logger.info(f"Best parameters: alpha={best_alpha}, k={best_k} (avg precision: {best_avg_precision:.4f})")
    
    return {
        'best_alpha': best_alpha,
        'best_k': best_k,
        'best_avg_precision': best_avg_precision,
        'grid_results': grid_results
    }


def main():
    """Main function for parameter tuning"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tune fusion parameters (alpha and k)')
    parser.add_argument('--test-queries', type=str, help='Path to JSON file with test queries')
    parser.add_argument('--tune-alpha', action='store_true', help='Tune alpha parameter')
    parser.add_argument('--tune-k', action='store_true', help='Tune k parameter')
    parser.add_argument('--tune-both', action='store_true', help='Tune both parameters (grid search)')
    parser.add_argument('--alpha', type=float, default=0.7, help='Fixed alpha for k tuning')
    parser.add_argument('--k', type=int, default=60, help='Fixed k for alpha tuning')
    parser.add_argument('--output', type=str, help='Output file for results (JSON)')
    
    args = parser.parse_args()
    
    # Load test queries
    test_queries = load_test_queries(args.test_queries)
    logger.info(f"Loaded {len(test_queries)} test queries")
    
    results = {}
    
    # Tune alpha
    if args.tune_alpha:
        alpha_results = tune_alpha(test_queries, k=args.k)
        results['alpha_tuning'] = alpha_results
        print(f"\n{'='*60}")
        print("Alpha Tuning Results")
        print(f"{'='*60}")
        print(f"Best alpha: {alpha_results['best_alpha']}")
        print(f"Best avg precision: {alpha_results['best_avg_precision']:.4f}")
        print(f"\nTop 5 alpha values:")
        sorted_alphas = sorted(alpha_results['alpha_results'], key=lambda x: x['avg_precision_at_k'], reverse=True)
        for i, alpha_result in enumerate(sorted_alphas[:5], 1):
            print(f"  {i}. alpha={alpha_result['alpha']:.2f}: precision={alpha_result['avg_precision_at_k']:.4f}, "
                  f"recall={alpha_result['avg_recall_at_k']:.4f}, f1={alpha_result['avg_f1_at_k']:.4f}, "
                  f"ndcg={alpha_result['avg_ndcg']:.4f}")
    
    # Tune k
    if args.tune_k:
        k_results = tune_k(test_queries, alpha=args.alpha)
        results['k_tuning'] = k_results
        print(f"\n{'='*60}")
        print("K Tuning Results")
        print(f"{'='*60}")
        print(f"Best k: {k_results['best_k']}")
        print(f"Best avg precision: {k_results['best_avg_precision']:.4f}")
        print(f"\nTop 5 k values:")
        sorted_ks = sorted(k_results['k_results'], key=lambda x: x['avg_precision_at_k'], reverse=True)
        for i, k_result in enumerate(sorted_ks[:5], 1):
            print(f"  {i}. k={k_result['k']}: precision={k_result['avg_precision_at_k']:.4f}, "
                  f"recall={k_result['avg_recall_at_k']:.4f}, f1={k_result['avg_f1_at_k']:.4f}, "
                  f"ndcg={k_result['avg_ndcg']:.4f}")
    
    # Tune both
    if args.tune_both:
        both_results = tune_both(test_queries)
        results['both_tuning'] = both_results
        print(f"\n{'='*60}")
        print("Grid Search Results")
        print(f"{'='*60}")
        print(f"Best alpha: {both_results['best_alpha']}")
        print(f"Best k: {both_results['best_k']}")
        print(f"Best avg precision: {both_results['best_avg_precision']:.4f}")
    
    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {args.output}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

