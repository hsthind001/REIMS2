"""
Citation Extraction Service

Extracts granular citations for every claim in LLM answers.
Provides sentence-level citations with exact source locations (document, page, line).
"""
import logging
import re
import time
from typing import List, Dict, Optional, Any, Tuple
from difflib import SequenceMatcher

from app.config.citation_config import citation_config
from app.services.hallucination_detector import HallucinationDetector, Claim

logger = logging.getLogger(__name__)

# Try to import fuzzywuzzy for better matching
try:
    from fuzzywuzzy import fuzz
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False
    logger.warning("fuzzywuzzy not available. Will use basic string matching.")


class Citation:
    """
    Represents a citation for a claim in an LLM-generated answer.
    
    A citation links a claim to its source(s), providing exact locations
    (page numbers, line numbers, coordinates) for verification.
    
    Attributes:
        citation_type: Type of citation ('document' or 'sql')
        claim_text: The claim text being cited
        sources: List of source dictionaries with metadata
        confidence: Confidence score of citation match (0-1)
    """
    
    def __init__(
        self,
        citation_type: str,  # 'document' or 'sql'
        claim_text: str,
        sources: List[Dict[str, Any]],
        confidence: float = 1.0
    ):
        """
        Initialize a citation.
        
        Args:
            citation_type: Type of citation ('document' or 'sql')
            claim_text: The claim text being cited
            sources: List of source dictionaries with metadata
            confidence: Confidence score of citation match (0-1, default: 1.0)
        """
        self.citation_type = citation_type
        self.claim_text = claim_text
        self.sources = sources
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert citation to dictionary representation.
        
        Returns:
            Dictionary containing all citation attributes
            
        Example:
            >>> citation = Citation('document', '$1,234,567.89', [{'page': 2}])
            >>> citation_dict = citation.to_dict()
            >>> print(citation_dict['type'])
            'document'
        """
        return {
            'claim': self.claim_text,
            'sources': self.sources,
            'confidence': self.confidence,
            'type': self.citation_type
        }


class CitationExtractor:
    """
    Extracts granular citations for claims in LLM answers
    
    Matches claims to source documents/chunks and extracts metadata
    (page numbers, line numbers, coordinates) for precise citations.
    """
    
    def __init__(self, db=None):
        """
        Initialize citation extractor
        
        Args:
            db: Database session (optional, for SQL citation extraction)
        """
        self.db = db
        self.hallucination_detector = HallucinationDetector(db) if db else None
    
    def extract_citations(
        self,
        answer: str,
        retrieved_chunks: Optional[List[Dict[str, Any]]] = None,
        sql_queries: Optional[List[str]] = None,
        sql_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Extract citations for all claims in answer
        
        Args:
            answer: LLM-generated answer text
            retrieved_chunks: List of retrieved document chunks (from RAG)
            sql_queries: List of SQL queries executed (optional)
            sql_results: List of SQL query results (optional)
        
        Returns:
            Dict with citations for each claim
        """
        if not answer or not answer.strip():
            return {
                'citations': [],
                'extraction_time_ms': 0.0,
                'total_claims': 0,
                'cited_claims': 0
            }
        
        start_time = time.time()
        
        try:
            # Extract numeric claims from answer
            if self.hallucination_detector:
                detection_result = self.hallucination_detector.detect_hallucinations(answer)
                claims = detection_result.get('claims', [])
            else:
                # Fallback: extract claims manually
                claims = self._extract_claims_manual(answer)
            
            if not claims:
                return {
                    'citations': [],
                    'extraction_time_ms': (time.time() - start_time) * 1000,
                    'total_claims': 0,
                    'cited_claims': 0
                }
            
            # Extract citations for each claim
            citations = []
            for claim_data in claims:
                if isinstance(claim_data, dict):
                    claim = Claim(
                        claim_type=claim_data.get('claim_type', 'unknown'),
                        value=claim_data.get('value', 0.0),
                        original_text=claim_data.get('original_text', ''),
                        context=claim_data.get('context', '')
                    )
                else:
                    claim = claim_data
                
                citation = self._extract_citation_for_claim(
                    claim=claim,
                    answer=answer,
                    retrieved_chunks=retrieved_chunks,
                    sql_queries=sql_queries,
                    sql_results=sql_results
                )
                
                if citation:
                    citations.append(citation)
            
            # Deduplicate citations
            if citation_config.DEDUPLICATE_SOURCES:
                citations = self._deduplicate_citations(citations)
            
            extraction_time_ms = (time.time() - start_time) * 1000
            
            result = {
                'citations': [c.to_dict() for c in citations],
                'extraction_time_ms': extraction_time_ms,
                'total_claims': len(claims),
                'cited_claims': len(citations)
            }
            
            logger.info(
                f"Extracted {len(citations)} citations for {len(claims)} claims "
                f"(time: {extraction_time_ms:.2f}ms)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Citation extraction failed: {e}", exc_info=True)
            return {
                'citations': [],
                'extraction_time_ms': (time.time() - start_time) * 1000,
                'total_claims': 0,
                'cited_claims': 0,
                'error': str(e)
            }
    
    def _extract_claims_manual(self, answer: str) -> List[Dict[str, Any]]:
        """
        Manually extract claims if hallucination detector not available.
        
        Fallback method for claim extraction when HallucinationDetector
        is not initialized. Uses basic regex patterns.
        
        Args:
            answer: Answer text to extract claims from
        
        Returns:
            List of claim dictionaries
        """
        claims = []
        
        # Extract currency
        currency_pattern = re.compile(r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:million|M|K|k)?', re.IGNORECASE)
        for match in currency_pattern.finditer(answer):
            claims.append({
                'claim_type': 'currency',
                'value': self._parse_currency_value(match.group(1), match.group(0)),
                'original_text': match.group(0),
                'context': self._get_context(answer, match.start(), match.end())
            })
        
        # Extract percentages
        percentage_pattern = re.compile(r'(\d+\.?\d*)\s*%')
        for match in percentage_pattern.finditer(answer):
            try:
                claims.append({
                    'claim_type': 'percentage',
                    'value': float(match.group(1)),
                    'original_text': match.group(0),
                    'context': self._get_context(answer, match.start(), match.end())
                })
            except ValueError:
                continue
        
        return claims
    
    def _parse_currency_value(self, value_str: str, suffix: str) -> float:
        """
        Parse currency value with M (million) and K (thousand) suffixes.
        
        Args:
            value_str: Numeric string (may include commas)
            suffix: Suffix string (may contain 'M', 'K', 'million', etc.)
        
        Returns:
            Parsed float value, or 0.0 if parsing fails
        """
        try:
            value_str = value_str.replace(',', '')
            base_value = float(value_str)
            
            if 'M' in suffix.upper() or 'MILLION' in suffix.upper():
                return base_value * 1000000
            elif 'K' in suffix.upper() or 'THOUSAND' in suffix.upper():
                return base_value * 1000
            else:
                return base_value
        except (ValueError, AttributeError):
            return 0.0
    
    def _get_context(self, text: str, start: int, end: int, window: int = 50) -> str:
        """
        Get context around a match position.
        
        Args:
            text: Full text string
            start: Start position of match
            end: End position of match
            window: Number of characters to include before/after (default: 50)
        
        Returns:
            Context string with surrounding text
        """
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end]
    
    def _extract_citation_for_claim(
        self,
        claim: Claim,
        answer: str,
        retrieved_chunks: Optional[List[Dict[str, Any]]] = None,
        sql_queries: Optional[List[str]] = None,
        sql_results: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Citation]:
        """
        Extract citation for a single claim
        
        Args:
            claim: Claim to find citation for
            answer: Full answer text
            retrieved_chunks: Retrieved document chunks
            sql_queries: SQL queries executed
            sql_results: SQL query results
        
        Returns:
            Citation object or None
        """
        sources = []
        
        # 1. Find in document chunks
        if retrieved_chunks:
            doc_sources = self._find_in_chunks(claim, retrieved_chunks)
            sources.extend(doc_sources)
        
        # 2. Find in SQL results
        if citation_config.INCLUDE_SQL_CITATIONS and sql_queries and sql_results:
            sql_sources = self._find_in_sql(claim, sql_queries, sql_results)
            sources.extend(sql_sources)
        
        if not sources:
            # No sources found
            return None
        
        # Limit sources per claim
        sources = sources[:citation_config.MAX_SOURCES_PER_CLAIM]
        
        # Calculate overall confidence
        confidence = max([s.get('confidence', 0.0) for s in sources]) if sources else 0.0
        
        return Citation(
            citation_type='document' if doc_sources else 'sql',
            claim_text=claim.original_text,
            sources=sources,
            confidence=confidence
        )
    
    def _find_in_chunks(
        self,
        claim: Claim,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Find claim in document chunks
        
        Args:
            claim: Claim to find
            chunks: List of document chunks
        
        Returns:
            List of source citations
        """
        sources = []
        
        # Search for claim value in chunks
        for chunk in chunks:
            chunk_text = chunk.get('chunk_text', '') or chunk.get('text', '')
            if not chunk_text:
                continue
            
            # Try to find claim value in chunk text
            match_result = self._match_claim_in_text(claim, chunk_text)
            
            if match_result['matched']:
                # Extract metadata
                source = {
                    'type': 'document',
                    'document_type': chunk.get('document_type', 'unknown'),
                    'chunk_id': chunk.get('chunk_id') or chunk.get('id'),
                    'document_id': chunk.get('document_id'),
                    'file_name': chunk.get('file_name'),
                    'confidence': match_result['confidence'],
                    'excerpt': match_result.get('excerpt', '')
                }
                
                # Add page number if available
                if citation_config.INCLUDE_PAGE_NUMBER:
                    page = chunk.get('metadata', {}).get('page') if isinstance(chunk.get('metadata'), dict) else None
                    if page is None:
                        page = chunk.get('page_number')
                    if page:
                        source['page'] = int(page)
                
                # Add line number if available
                if citation_config.INCLUDE_LINE_NUMBER:
                    line = chunk.get('metadata', {}).get('line') if isinstance(chunk.get('metadata'), dict) else None
                    if line is None:
                        line = chunk.get('line_number')
                    if line:
                        source['line'] = int(line)
                
                # Add coordinates if available
                metadata = chunk.get('metadata', {})
                if isinstance(metadata, dict):
                    if 'x0' in metadata and 'y0' in metadata:
                        source['coordinates'] = {
                            'x0': metadata.get('x0'),
                            'y0': metadata.get('y0'),
                            'x1': metadata.get('x1'),
                            'y1': metadata.get('y1')
                        }
                
                # Add excerpt if enabled
                if citation_config.INCLUDE_EXCERPT:
                    excerpt = self._extract_excerpt(chunk_text, match_result.get('match_position', 0))
                    source['excerpt'] = excerpt
                
                sources.append(source)
        
        # Sort by confidence (highest first)
        sources.sort(key=lambda x: x.get('confidence', 0.0), reverse=True)
        
        return sources
    
    def _match_claim_in_text(self, claim: Claim, text: str) -> Dict[str, Any]:
        """
        Match claim value in text.
        
        Attempts exact match first, then fuzzy matching if available.
        For currency claims, also searches for value in different formats
        (e.g., $1.2M vs $1,200,000).
        
        Args:
            claim: Claim to match
            text: Text to search in
        
        Returns:
            Dictionary with match result:
            {
                'matched': bool,
                'confidence': float,  # 0-1
                'match_position': int,
                'excerpt': str
            }
        """
        # Normalize text for matching
        text_lower = text.lower()
        claim_text_lower = claim.original_text.lower()
        
        # Try exact match first
        if claim_text_lower in text_lower:
            position = text_lower.find(claim_text_lower)
            return {
                'matched': True,
                'confidence': 1.0,
                'match_position': position,
                'excerpt': self._extract_excerpt(text, position)
            }
        
        # Try fuzzy match for claim value
        if claim.claim_type == 'currency':
            # Search for currency patterns
            currency_patterns = [
                re.compile(rf'\${re.escape(str(int(claim.value)))}', re.IGNORECASE),
                re.compile(rf'\${re.escape(str(int(claim.value / 1000000)))}M', re.IGNORECASE),
                re.compile(rf'\${re.escape(str(int(claim.value / 1000)))}K', re.IGNORECASE),
            ]
            
            for pattern in currency_patterns:
                match = pattern.search(text)
                if match:
                    return {
                        'matched': True,
                        'confidence': 0.9,
                        'match_position': match.start(),
                        'excerpt': self._extract_excerpt(text, match.start())
                    }
        
        # Try fuzzy string matching
        if FUZZYWUZZY_AVAILABLE:
            # Find best matching substring
            words = text_lower.split()
            claim_words = claim_text_lower.split()
            
            best_match = 0.0
            best_position = 0
            
            for i in range(len(words) - len(claim_words) + 1):
                substring = ' '.join(words[i:i+len(claim_words)])
                similarity = fuzz.ratio(substring, claim_text_lower) / 100.0
                
                if similarity > best_match:
                    best_match = similarity
                    best_position = i
            
            if best_match >= citation_config.FUZZY_MATCH_THRESHOLD:
                return {
                    'matched': True,
                    'confidence': best_match,
                    'match_position': best_position,
                    'excerpt': self._extract_excerpt(text, best_position)
                }
        else:
            # Basic substring matching
            similarity = SequenceMatcher(None, claim_text_lower, text_lower[:len(claim_text_lower) * 2]).ratio()
            if similarity >= citation_config.FUZZY_MATCH_THRESHOLD:
                return {
                    'matched': True,
                    'confidence': similarity,
                    'match_position': 0,
                    'excerpt': self._extract_excerpt(text, 0)
                }
        
        return {
            'matched': False,
            'confidence': 0.0
        }
    
    def _extract_excerpt(self, text: str, position: int) -> str:
        """
        Extract excerpt around position for citation display.
        
        Args:
            text: Full text string
            position: Position to extract excerpt around
        
        Returns:
            Excerpt string with ellipsis if truncated
        """
        window = citation_config.EXCERPT_WINDOW
        start = max(0, position - window)
        end = min(len(text), position + window)
        excerpt = text[start:end]
        
        # Add ellipsis if truncated
        if start > 0:
            excerpt = '...' + excerpt
        if end < len(text):
            excerpt = excerpt + '...'
        
        return excerpt.strip()
    
    def _find_in_sql(
        self,
        claim: Claim,
        sql_queries: List[str],
        sql_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Find claim in SQL results
        
        Args:
            claim: Claim to find
            sql_queries: SQL queries executed
            sql_results: SQL query results
        
        Returns:
            List of SQL source citations
        """
        sources = []
        
        # Check if claim value appears in SQL results
        for i, result in enumerate(sql_results):
            # Search for claim value in result values
            if self._value_in_sql_result(claim, result):
                query = sql_queries[i] if i < len(sql_queries) else None
                
                source = {
                    'type': 'sql',
                    'query': query,
                    'value': self._extract_value_from_result(claim, result),
                    'confidence': 0.95  # High confidence for SQL results
                }
                
                sources.append(source)
        
        return sources
    
    def _value_in_sql_result(self, claim: Claim, result: Dict[str, Any]) -> bool:
        """Check if claim value appears in SQL result"""
        # Check numeric values in result
        tolerance = 0.05  # 5% tolerance
        
        def check_value(value):
            if isinstance(value, (int, float)):
                if claim.claim_type == 'currency':
                    min_val = claim.value * (1 - tolerance)
                    max_val = claim.value * (1 + tolerance)
                    return min_val <= value <= max_val
                elif claim.claim_type in ['percentage', 'ratio']:
                    min_val = claim.value * (1 - tolerance)
                    max_val = claim.value * (1 + tolerance)
                    return min_val <= value <= max_val
            return False
        
        # Recursively check result dictionary
        if isinstance(result, dict):
            for key, value in result.items():
                if check_value(value):
                    return True
                elif isinstance(value, (dict, list)):
                    if self._value_in_sql_result(claim, value):
                        return True
        elif isinstance(result, list):
            for item in result:
                if self._value_in_sql_result(claim, item):
                    return True
        
        return False
    
    def _extract_value_from_result(self, claim: Claim, result: Dict[str, Any]) -> Optional[float]:
        """
        Extract matching value from SQL result.
        
        Recursively searches SQL result for value matching claim within
        tolerance. Returns the matching value for citation.
        
        Args:
            claim: Claim to match
            result: SQL result dictionary or list
        
        Returns:
            Matching value if found, None otherwise
        """
        tolerance = 0.05
        
        def find_value(obj):
            if isinstance(obj, (int, float)):
                if claim.claim_type == 'currency':
                    min_val = claim.value * (1 - tolerance)
                    max_val = claim.value * (1 + tolerance)
                    if min_val <= obj <= max_val:
                        return obj
            elif isinstance(obj, dict):
                for v in obj.values():
                    found = find_value(v)
                    if found is not None:
                        return found
            elif isinstance(obj, list):
                for item in obj:
                    found = find_value(item)
                    if found is not None:
                        return found
            return None
        
        return find_value(result)
    
    def _deduplicate_citations(self, citations: List[Citation]) -> List[Citation]:
        """
        Deduplicate citations with similar sources.
        
        Removes duplicate sources from citations based on document ID,
        chunk ID, and page number.
        
        Args:
            citations: List of citations to deduplicate
        
        Returns:
            Deduplicated list of citations
        """
        if not citation_config.DEDUPLICATE_SOURCES:
            return citations
        
        deduplicated = []
        seen_sources = set()
        
        for citation in citations:
            # Create signature for each source
            citation_sources = []
            
            for source in citation.sources:
                # Create signature based on type
                if source.get('type') == 'document':
                    sig = f"doc:{source.get('document_id')}:{source.get('chunk_id')}:{source.get('page', '')}"
                elif source.get('type') == 'sql':
                    sig = f"sql:{source.get('query', '')[:50]}"
                else:
                    sig = str(source)
                
                # Check if we've seen this source
                if sig not in seen_sources:
                    seen_sources.add(sig)
                    citation_sources.append(source)
            
            # Only keep citation if it has sources
            if citation_sources:
                citation.sources = citation_sources
                deduplicated.append(citation)
        
        return deduplicated
    
    def format_citation_inline(self, citation: Citation) -> str:
        """
        Format citation as inline text
        
        Args:
            citation: Citation to format
        
        Returns:
            Formatted citation string
        """
        if not citation.sources:
            return citation.claim_text
        
        source_strs = []
        for source in citation.sources[:citation_config.MAX_SOURCES_PER_CLAIM]:
            if source.get('type') == 'document':
                parts = []
                
                doc_type = source.get('document_type', 'document').replace('_', ' ').title()
                parts.append(doc_type)
                
                if citation_config.INCLUDE_PAGE_NUMBER and source.get('page'):
                    parts.append(f"Page {source['page']}")
                
                if citation_config.INCLUDE_LINE_NUMBER and source.get('line'):
                    parts.append(f"Line {source['line']}")
                
                source_str = ', '.join(parts)
                source_strs.append(f"[Source: {source_str}]")
            
            elif source.get('type') == 'sql':
                source_strs.append("[Source: Database Query]")
        
        if source_strs:
            return f"{citation.claim_text} {' '.join(source_strs)}"
        
        return citation.claim_text
    
    def format_citations_for_api(self, citations: List[Citation]) -> List[Dict[str, Any]]:
        """
        Format citations for API response.
        
        Converts Citation objects to dictionary format suitable for JSON
        API responses. Includes all source metadata and confidence scores.
        
        Args:
            citations: List of Citation objects to format
        
        Returns:
            List of formatted citation dictionaries
            
        Example:
            >>> citations = [Citation('document', '$1,234,567.89', [...])]
            >>> api_citations = extractor.format_citations_for_api(citations)
            >>> print(api_citations[0]['claim'])
            '$1,234,567.89'
        """
        formatted = []
        
        for citation in citations:
            formatted.append({
                'claim': citation.claim_text,
                'sources': citation.sources,
                'confidence': citation.confidence,
                'type': citation.citation_type
            })
        
        return formatted

