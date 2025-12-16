"""
Fusion Evaluation Metrics

Provides evaluation metrics for assessing fusion performance,
including precision, recall, F1, NDCG, and MRR.
"""
import logging
from typing import List, Dict, Any, Optional
import math

logger = logging.getLogger(__name__)


class FusionEvaluation:
    """
    Evaluation metrics for fusion results
    
    Provides metrics like precision@k, recall@k, F1@k, NDCG, and MRR.
    """
    
    def __init__(self, top_k: int = 20):
        """
        Initialize evaluation metrics
        
        Args:
            top_k: Top-k for precision/recall calculations
        """
        self.top_k = top_k
    
    def evaluate(
        self,
        fused_results: List[Dict[str, Any]],
        ground_truth: List[int],
        top_k: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Evaluate fused results against ground truth
        
        Args:
            fused_results: List of fused results with 'chunk_id'
            ground_truth: List of relevant chunk_ids
            top_k: Top-k for evaluation (default: self.top_k)
        
        Returns:
            Dict with evaluation metrics
        """
        if top_k is None:
            top_k = self.top_k
        
        if not fused_results:
            return {
                'precision_at_k': 0.0,
                'recall_at_k': 0.0,
                'f1_at_k': 0.0,
                'ndcg': 0.0,
                'mrr': 0.0,
                'relevant_retrieved': 0,
                'total_retrieved': 0,
                'total_relevant': len(ground_truth)
            }
        
        # Get chunk IDs from results
        retrieved_chunk_ids = [r.get('chunk_id') for r in fused_results[:top_k] if r.get('chunk_id')]
        ground_truth_set = set(ground_truth)
        
        # Calculate metrics
        precision = self.precision_at_k(retrieved_chunk_ids, ground_truth_set, top_k)
        recall = self.recall_at_k(retrieved_chunk_ids, ground_truth_set, ground_truth)
        f1 = self.f1_at_k(precision, recall)
        ndcg = self.ndcg(fused_results[:top_k], ground_truth_set)
        mrr = self.mrr(fused_results, ground_truth_set)
        
        relevant_retrieved = len(set(retrieved_chunk_ids) & ground_truth_set)
        
        return {
            'precision_at_k': precision,
            'recall_at_k': recall,
            'f1_at_k': f1,
            'ndcg': ndcg,
            'mrr': mrr,
            'relevant_retrieved': relevant_retrieved,
            'total_retrieved': len(retrieved_chunk_ids),
            'total_relevant': len(ground_truth)
        }
    
    def precision_at_k(
        self,
        retrieved: List[int],
        ground_truth: set,
        k: Optional[int] = None
    ) -> float:
        """
        Calculate precision@k
        
        Args:
            retrieved: List of retrieved chunk IDs
            ground_truth: Set of relevant chunk IDs
            k: Top-k for calculation (default: len(retrieved))
        
        Returns:
            Precision@k score (0-1)
        """
        if k is None:
            k = len(retrieved)
        
        if k == 0:
            return 0.0
        
        relevant_retrieved = sum(1 for chunk_id in retrieved[:k] if chunk_id in ground_truth)
        return relevant_retrieved / k
    
    def recall_at_k(
        self,
        retrieved: List[int],
        ground_truth: List[int],
        k: Optional[int] = None
    ) -> float:
        """
        Calculate recall@k
        
        Args:
            retrieved: List of retrieved chunk IDs
            ground_truth: List of relevant chunk IDs
            k: Top-k for calculation (default: len(retrieved))
        
        Returns:
            Recall@k score (0-1)
        """
        if k is None:
            k = len(retrieved)
        
        ground_truth_set = set(ground_truth)
        total_relevant = len(ground_truth_set)
        
        if total_relevant == 0:
            return 0.0
        
        relevant_retrieved = sum(1 for chunk_id in retrieved[:k] if chunk_id in ground_truth_set)
        return relevant_retrieved / total_relevant
    
    def f1_at_k(self, precision: float, recall: float) -> float:
        """
        Calculate F1@k from precision and recall
        
        Args:
            precision: Precision@k score
            recall: Recall@k score
        
        Returns:
            F1@k score (0-1)
        """
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)
    
    def ndcg(
        self,
        results: List[Dict[str, Any]],
        ground_truth: set,
        k: Optional[int] = None
    ) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain (NDCG)
        
        Args:
            results: List of results with 'chunk_id'
            ground_truth: Set of relevant chunk IDs
            k: Top-k for calculation (default: len(results))
        
        Returns:
            NDCG score (0-1)
        """
        if k is None:
            k = len(results)
        
        if k == 0:
            return 0.0
        
        # Calculate DCG
        dcg = 0.0
        for i, result in enumerate(results[:k], start=1):
            chunk_id = result.get('chunk_id')
            if chunk_id in ground_truth:
                # Relevance score: 1 if relevant, 0 otherwise
                relevance = 1.0
                dcg += relevance / math.log2(i + 1)
        
        # Calculate IDCG (ideal DCG - all relevant items at top)
        idcg = 0.0
        num_relevant = min(len(ground_truth), k)
        for i in range(1, num_relevant + 1):
            idcg += 1.0 / math.log2(i + 1)
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    def mrr(
        self,
        results: List[Dict[str, Any]],
        ground_truth: set
    ) -> float:
        """
        Calculate Mean Reciprocal Rank (MRR)
        
        Args:
            results: List of results with 'chunk_id'
            ground_truth: Set of relevant chunk IDs
        
        Returns:
            MRR score (0-1)
        """
        for rank, result in enumerate(results, start=1):
            chunk_id = result.get('chunk_id')
            if chunk_id in ground_truth:
                return 1.0 / rank
        
        return 0.0
    
    def evaluate_multiple_queries(
        self,
        query_results: List[Dict[str, Any]],
        ground_truths: List[List[int]]
    ) -> Dict[str, float]:
        """
        Evaluate multiple queries and return average metrics
        
        Args:
            query_results: List of result lists (one per query)
            ground_truths: List of ground truth lists (one per query)
        
        Returns:
            Dict with average metrics across all queries
        """
        if len(query_results) != len(ground_truths):
            raise ValueError("Number of query results must match number of ground truth sets")
        
        all_metrics = []
        for results, ground_truth in zip(query_results, ground_truths):
            metrics = self.evaluate(results, ground_truth)
            all_metrics.append(metrics)
        
        # Calculate averages
        avg_metrics = {}
        for metric_name in all_metrics[0].keys():
            if isinstance(all_metrics[0][metric_name], (int, float)):
                avg_metrics[f'avg_{metric_name}'] = sum(m[metric_name] for m in all_metrics) / len(all_metrics)
            else:
                avg_metrics[f'avg_{metric_name}'] = all_metrics[0][metric_name]
        
        return avg_metrics

