"""
RAG Accuracy Diagnostics and Evaluation

Diagnoses accuracy issues in retrieval and provides actionable fixes.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class RAGAccuracyDiagnostics:
    """
    Diagnose accuracy issues in RAG retrieval.
    
    Identifies:
    - Why hybrid search performs worse than semantic alone
    - Metadata filtering issues
    - Chunking problems
    - Score normalization issues
    """
    
    def __init__(self):
        self.diagnostics = {}
    
    def diagnose_hybrid_degradation(
        self,
        semantic_results: List[Dict],
        bm25_results: List[Dict],
        fused_results: List[Dict],
        ground_truth: List[int]
    ) -> Dict[str, Any]:
        """
        Diagnose why hybrid search performs worse than semantic alone.
        
        Args:
            semantic_results: Semantic search results
            bm25_results: BM25 search results
            fused_results: Fused results
            ground_truth: Relevant chunk IDs
        
        Returns:
            Diagnostic report
        """
        report = {
            'semantic_precision': self._calculate_precision(semantic_results, ground_truth, k=5),
            'bm25_precision': self._calculate_precision(bm25_results, ground_truth, k=5),
            'fused_precision': self._calculate_precision(fused_results, ground_truth, k=5),
            'issues': []
        }
        
        # Issue 1: BM25 returning irrelevant results
        bm25_relevant = set(bm25_results[:5]) & set(ground_truth)
        semantic_relevant = set(semantic_results[:5]) & set(ground_truth)
        
        if len(bm25_relevant) < len(semantic_relevant):
            report['issues'].append({
                'type': 'bm25_low_precision',
                'severity': 'high',
                'description': f'BM25 has lower precision ({len(bm25_relevant)}/5) than semantic ({len(semantic_relevant)}/5)',
                'recommendation': 'Improve BM25 filtering or reduce BM25 weight in fusion'
            })
        
        # Issue 2: Score normalization problems
        semantic_scores = [r.get('similarity', 0) for r in semantic_results[:5]]
        bm25_scores = [r.get('score', 0) for r in bm25_results[:5]]
        
        if max(bm25_scores) > 10 * max(semantic_scores):
            report['issues'].append({
                'type': 'score_scale_mismatch',
                'severity': 'high',
                'description': f'BM25 scores ({max(bm25_scores):.2f}) much larger than semantic ({max(semantic_scores):.2f})',
                'recommendation': 'Normalize BM25 scores to 0-1 range before fusion'
            })
        
        # Issue 3: RRF giving too much weight to BM25
        if report['fused_precision'] < report['semantic_precision']:
            report['issues'].append({
                'type': 'rrf_alpha_too_low',
                'severity': 'medium',
                'description': f'Fused precision ({report["fused_precision"]:.2%}) lower than semantic ({report["semantic_precision"]:.2%})',
                'recommendation': 'Increase RRF alpha (semantic weight) or use semantic-only for this query type'
            })
        
        # Issue 4: Overlap analysis
        overlap = set([r['chunk_id'] for r in semantic_results[:10]]) & set([r['chunk_id'] for r in bm25_results[:10]])
        if len(overlap) < 3:
            report['issues'].append({
                'type': 'low_result_overlap',
                'severity': 'medium',
                'description': f'Only {len(overlap)} chunks appear in both top-10 results',
                'recommendation': 'BM25 and semantic are finding different chunks - may indicate query ambiguity'
            })
        
        return report
    
    def diagnose_metadata_filtering(
        self,
        query: str,
        results: List[Dict],
        expected_property_id: Optional[int] = None,
        expected_period_id: Optional[int] = None,
        expected_document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Diagnose metadata filtering issues.
        
        Args:
            query: Original query
            results: Retrieved results
            expected_property_id: Expected property ID (if extractable from query)
            expected_period_id: Expected period ID (if extractable from query)
            expected_document_type: Expected document type
        
        Returns:
            Diagnostic report
        """
        report = {
            'total_results': len(results),
            'metadata_violations': [],
            'extracted_entities': {}
        }
        
        # Extract entities from query
        extracted = self._extract_entities(query)
        report['extracted_entities'] = extracted
        
        # Check for violations
        for i, result in enumerate(results[:10]):
            violations = []
            
            if expected_property_id and result.get('property_id') != expected_property_id:
                violations.append(f'Wrong property_id: got {result.get("property_id")}, expected {expected_property_id}')
            
            if expected_period_id and result.get('period_id') != expected_period_id:
                violations.append(f'Wrong period_id: got {result.get("period_id")}, expected {expected_period_id}')
            
            if expected_document_type and result.get('document_type') != expected_document_type:
                violations.append(f'Wrong document_type: got {result.get("document_type")}, expected {expected_document_type}')
            
            if violations:
                report['metadata_violations'].append({
                    'rank': i + 1,
                    'chunk_id': result.get('chunk_id'),
                    'violations': violations,
                    'chunk_text_preview': result.get('chunk_text', '')[:100]
                })
        
        return report
    
    def diagnose_chunking_issues(
        self,
        query: str,
        results: List[Dict],
        ground_truth_chunks: List[Dict]
    ) -> Dict[str, Any]:
        """
        Diagnose chunking strategy issues.
        
        Args:
            query: Query text
            results: Retrieved results
            ground_truth_chunks: Ground truth chunks with full context
        
        Returns:
            Diagnostic report
        """
        report = {
            'context_loss': [],
            'overlap_issues': [],
            'chunk_boundary_problems': []
        }
        
        # Check if retrieved chunks have enough context
        for result in results[:5]:
            chunk_text = result.get('chunk_text', '')
            query_terms = set(query.lower().split())
            chunk_terms = set(chunk_text.lower().split())
            
            # Check if chunk contains query terms
            missing_terms = query_terms - chunk_terms
            if missing_terms:
                report['context_loss'].append({
                    'chunk_id': result.get('chunk_id'),
                    'missing_terms': list(missing_terms),
                    'chunk_length': len(chunk_text)
                })
        
        # Check chunk boundaries (if we have ground truth)
        if ground_truth_chunks:
            for result in results[:5]:
                chunk_id = result.get('chunk_id')
                gt_chunk = next((c for c in ground_truth_chunks if c.get('id') == chunk_id), None)
                
                if gt_chunk:
                    # Check if chunk is split at wrong boundary
                    if result.get('chunk_index', 0) > 0:
                        # Check if previous chunk has important context
                        prev_chunk = next(
                            (c for c in ground_truth_chunks if c.get('chunk_index') == result.get('chunk_index', 0) - 1),
                            None
                        )
                        if prev_chunk:
                            # Check if query terms appear in previous chunk
                            prev_text = prev_chunk.get('chunk_text', '').lower()
                            query_in_prev = any(term in prev_text for term in query.lower().split())
                            
                            if query_in_prev:
                                report['chunk_boundary_problems'].append({
                                    'chunk_id': chunk_id,
                                    'issue': 'Query context split across chunks',
                                    'current_chunk_index': result.get('chunk_index'),
                                    'previous_chunk_has_context': True
                                })
        
        return report
    
    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """
        Extract entities from query (property names, periods, document types).
        
        Args:
            query: Query text
        
        Returns:
            Dict with extracted entities
        """
        entities = {
            'property_names': [],
            'periods': [],
            'document_types': [],
            'metrics': []
        }
        
        # Extract property names (common patterns)
        property_patterns = [
            r'\b(Eastern Shore|Wendover|Property [A-Z]+)\b',
            r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b'  # Two-word capitalized names
        ]
        
        for pattern in property_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities['property_names'].extend(matches)
        
        # Extract periods (Q3, Q4, 2024, etc.)
        period_patterns = [
            r'\bQ([1-4])\b',
            r'\b(20\d{2})\b',  # Years
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b'
        ]
        
        for pattern in period_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities['periods'].extend(matches)
        
        # Extract document types
        doc_type_keywords = {
            'income_statement': ['income', 'revenue', 'profit', 'loss'],
            'balance_sheet': ['balance', 'assets', 'liabilities'],
            'cash_flow': ['cash flow', 'cashflow'],
            'rent_roll': ['rent', 'lease', 'tenant']
        }
        
        query_lower = query.lower()
        for doc_type, keywords in doc_type_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                entities['document_types'].append(doc_type)
        
        # Extract metrics
        metric_keywords = ['NOI', 'DSCR', 'occupancy', 'revenue', 'expenses', 'profit', 'loss']
        for metric in metric_keywords:
            if metric.lower() in query_lower:
                entities['metrics'].append(metric)
        
        return entities
    
    def _calculate_precision(self, results: List[Dict], ground_truth: List[int], k: int = 5) -> float:
        """Calculate precision@k."""
        if not results or not ground_truth:
            return 0.0
        
        top_k_ids = [r.get('chunk_id') for r in results[:k]]
        relevant = set(top_k_ids) & set(ground_truth)
        
        return len(relevant) / min(k, len(results))
    
    def generate_fix_recommendations(
        self,
        diagnostics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate actionable fix recommendations based on diagnostics.
        
        Args:
            diagnostics: Diagnostic results
        
        Returns:
            List of recommendations with priority
        """
        recommendations = []
        
        # Check hybrid degradation issues
        if 'hybrid_degradation' in diagnostics:
            hd = diagnostics['hybrid_degradation']
            for issue in hd.get('issues', []):
                if issue['type'] == 'bm25_low_precision':
                    recommendations.append({
                        'priority': 'HIGH',
                        'issue': 'BM25 returning irrelevant results',
                        'fix': 'Improve BM25 metadata filtering or reduce BM25 weight',
                        'code_changes': [
                            'Add strict metadata filtering in BM25 search',
                            'Normalize BM25 scores before fusion',
                            'Consider disabling BM25 for queries with low keyword match'
                        ]
                    })
                
                if issue['type'] == 'score_scale_mismatch':
                    recommendations.append({
                        'priority': 'HIGH',
                        'issue': 'BM25 and semantic scores on different scales',
                        'fix': 'Normalize both to 0-1 range before fusion',
                        'code_changes': [
                            'Normalize BM25 scores: score / max_score',
                            'Ensure semantic scores are already 0-1 (cosine similarity)'
                        ]
                    })
                
                if issue['type'] == 'rrf_alpha_too_low':
                    recommendations.append({
                        'priority': 'MEDIUM',
                        'issue': 'RRF alpha too low (giving too much weight to BM25)',
                        'fix': 'Increase alpha to 0.8-0.9 or use adaptive alpha',
                        'code_changes': [
                            'Increase default alpha from 0.7 to 0.85',
                            'Implement query-type-based alpha selection'
                        ]
                    })
        
        # Check metadata filtering issues
        if 'metadata_filtering' in diagnostics:
            mf = diagnostics['metadata_filtering']
            if mf.get('metadata_violations'):
                recommendations.append({
                    'priority': 'HIGH',
                    'issue': 'Metadata filtering not working correctly',
                    'fix': 'Enforce metadata filters in retrieval, not post-filtering',
                    'code_changes': [
                        'Apply property_id/period_id filters in Pinecone query',
                        'Apply filters in BM25 before scoring',
                        'Add entity extraction from query to set filters'
                    ]
                })
        
        # Check chunking issues
        if 'chunking_issues' in diagnostics:
            ci = diagnostics['chunking_issues']
            if ci.get('context_loss') or ci.get('chunk_boundary_problems'):
                recommendations.append({
                    'priority': 'MEDIUM',
                    'issue': 'Chunking splitting important context',
                    'fix': 'Improve chunking strategy with better boundaries',
                    'code_changes': [
                        'Increase chunk overlap from 100 to 200 tokens',
                        'Use sentence-aware chunking',
                        'Preserve table structure in chunks'
                    ]
                })
        
        return recommendations

