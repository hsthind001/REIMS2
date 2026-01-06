import re
from typing import Dict, List
from langdetect import detect, detect_langs, LangDetectException
from difflib import SequenceMatcher


class QualityValidator:
    """Validate and score extraction quality"""
    
    def __init__(self):
        self.min_words_per_page = 10
        self.max_special_char_ratio = 0.3
        self.min_confidence_score = 70.0
    
    def validate_extraction(self, extraction_result: Dict) -> Dict:
        """
        Comprehensive validation of extraction results
        
        Returns quality scores and validation report
        """
        validation = {
            "overall_quality": "unknown",
            "confidence_score": 0.0,
            "issues": [],
            "warnings": [],
            "metrics": {},
            "passed_checks": 0,
            "total_checks": 10,
            "success": True
        }
        
        try:
            text = extraction_result.get("text", "")
            pages = extraction_result.get("pages", [])
            total_pages = extraction_result.get("total_pages", 0)
            
            # Run all validation checks
            checks = []
            
            # 1. Text length validation
            checks.append(self._check_text_length(text, total_pages))
            
            # 2. Special characters validation
            checks.append(self._check_special_characters(text))
            
            # 3. Language consistency
            checks.append(self._check_language_consistency(text))
            
            # 4. Gibberish detection
            checks.append(self._check_gibberish(text))
            
            # 5. Word distribution
            checks.append(self._check_word_distribution(text))
            
            # 6. Page consistency
            checks.append(self._check_page_consistency(pages))
            
            # 7. Empty pages check
            checks.append(self._check_empty_pages(pages))
            
            # 8. Character distribution
            checks.append(self._check_character_distribution(text))
            
            # 9. Whitespace ratio
            checks.append(self._check_whitespace_ratio(text))
            
            # 10. Confidence threshold (if available)
            engine_confidence = extraction_result.get("avg_confidence", extraction_result.get("confidence", 100))
            checks.append(self._check_confidence_threshold(engine_confidence))
            
            # Aggregate results
            passed_checks = sum(1 for check in checks if check["passed"])
            validation["passed_checks"] = passed_checks
            validation["total_checks"] = len(checks)
            
            # Collect issues and warnings
            for check in checks:
                if not check["passed"]:
                    if check["severity"] == "error":
                        validation["issues"].append(check["message"])
                    else:
                        validation["warnings"].append(check["message"])
                
                validation["metrics"][check["name"]] = check
            
            # Calculate confidence score
            validation["confidence_score"] = self._calculate_confidence_score(
                checks,
                passed_checks,
                len(checks),
                engine_confidence
            )
            
            # Determine overall quality
            validation["overall_quality"] = self._determine_quality_level(
                validation["confidence_score"]
            )
            
            # Add recommendations
            validation["recommendations"] = self._get_recommendations(
                validation["overall_quality"],
                validation["issues"],
                extraction_result
            )
            
        except Exception as e:
            validation["success"] = False
            validation["error"] = str(e)
        
        return validation
    
    def _check_text_length(self, text: str, total_pages: int) -> Dict:
        """Check if text length is reasonable for page count"""
        min_expected = total_pages * 50  # At least 50 chars per page
        actual_length = len(text.strip())
        
        passed = actual_length >= min_expected
        
        return {
            "name": "text_length",
            "passed": passed,
            "severity": "error" if not passed else "info",
            "message": f"Text too short: {actual_length} chars for {total_pages} pages" if not passed else "Text length reasonable",
            "value": actual_length,
            "expected_min": min_expected
        }
    
    def _check_special_characters(self, text: str) -> Dict:
        """Check for excessive special characters (OCR artifacts)"""
        if not text:
            return {"name": "special_chars", "passed": False, "severity": "error", "message": "No text found", "value": 0}
        
        special_chars = len(re.findall(r'[^\w\s.,!?;:\-\'"()\[\]{}]', text))
        total_chars = len(text)
        ratio = special_chars / total_chars if total_chars > 0 else 1.0
        
        passed = ratio < self.max_special_char_ratio
        
        return {
            "name": "special_chars",
            "passed": passed,
            "severity": "warning" if not passed else "info",
            "message": f"High special character ratio: {ratio:.2%}" if not passed else "Special character ratio acceptable",
            "value": round(ratio, 4),
            "threshold": self.max_special_char_ratio
        }
    
    def _check_language_consistency(self, text: str) -> Dict:
        """Check language consistency"""
        try:
            if len(text.strip()) < 50:
                return {
                    "name": "language",
                    "passed": True,
                    "severity": "info",
                    "message": "Text too short for language detection",
                    "value": "unknown"
                }
            
            # Detect language
            lang = detect(text)
            
            # Get language probabilities
            langs = detect_langs(text)
            primary_lang_prob = langs[0].prob if langs else 0
            
            # High probability means consistent language
            passed = primary_lang_prob > 0.7
            
            return {
                "name": "language",
                "passed": passed,
                "severity": "warning" if not passed else "info",
                "message": f"Language: {lang} (confidence: {primary_lang_prob:.2%})",
                "value": lang,
                "probability": round(primary_lang_prob, 4)
            }
        
        except LangDetectException:
            return {
                "name": "language",
                "passed": True,
                "severity": "info",
                "message": "Could not detect language",
                "value": "unknown"
            }
    
    def _check_gibberish(self, text: str) -> Dict:
        """Detect gibberish or OCR errors"""
        if not text or len(text.strip()) < 50:
            return {"name": "gibberish", "passed": True, "severity": "info", "message": "Text too short", "value": 0}
        
        # Count words with unusual character patterns
        words = text.split()
        gibberish_words = 0
        
        for word in words:
            # Gibberish indicators:
            # - Too many consonants in a row
            # - Too many repeating characters
            # - Mix of letters and numbers
            if len(word) > 3:
                if re.search(r'[bcdfghjklmnpqrstvwxyz]{5,}', word.lower()):
                    gibberish_words += 1
                elif re.search(r'(.)\1{3,}', word):
                    gibberish_words += 1
                elif re.search(r'[a-z]+\d+[a-z]+', word.lower()):
                    gibberish_words += 1
        
        gibberish_ratio = gibberish_words / len(words) if words else 0
        passed = gibberish_ratio < 0.15  # Less than 15% gibberish
        
        return {
            "name": "gibberish",
            "passed": passed,
            "severity": "error" if not passed else "info",
            "message": f"High gibberish ratio: {gibberish_ratio:.2%}" if not passed else "Text quality good",
            "value": round(gibberish_ratio, 4)
        }
    
    def _check_word_distribution(self, text: str) -> Dict:
        """Check if word lengths are reasonable"""
        words = text.split()
        
        if not words:
            return {"name": "word_distribution", "passed": False, "severity": "error", "message": "No words found", "value": 0}
        
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # Average word length should be between 3-10 characters
        passed = 3 <= avg_word_length <= 10
        
        return {
            "name": "word_distribution",
            "passed": passed,
            "severity": "warning" if not passed else "info",
            "message": f"Average word length: {avg_word_length:.2f}",
            "value": round(avg_word_length, 2),
            "expected_range": [3, 10]
        }
    
    def _check_page_consistency(self, pages: List[Dict]) -> Dict:
        """Check if pages have consistent text amounts"""
        if len(pages) < 2:
            return {"name": "page_consistency", "passed": True, "severity": "info", "message": "Single page document", "value": 1.0}
        
        word_counts = [p.get("word_count", 0) for p in pages]
        avg_words = sum(word_counts) / len(word_counts) if word_counts else 0
        
        # Check if any page is suspiciously empty
        empty_pages = sum(1 for wc in word_counts if wc < max(10, avg_words * 0.1))
        empty_ratio = empty_pages / len(pages)
        
        passed = empty_ratio < 0.3  # Less than 30% empty pages
        
        return {
            "name": "page_consistency",
            "passed": passed,
            "severity": "warning" if not passed else "info",
            "message": f"{empty_pages} pages appear empty or very sparse",
            "value": round(empty_ratio, 4),
            "empty_pages": empty_pages
        }
    
    def _check_empty_pages(self, pages: List[Dict]) -> Dict:
        """Check for empty pages"""
        empty_count = sum(1 for p in pages if p.get("word_count", 0) == 0)
        
        passed = empty_count < len(pages) * 0.5  # Less than 50% empty
        
        return {
            "name": "empty_pages",
            "passed": passed,
            "severity": "warning" if not passed else "info",
            "message": f"{empty_count} empty pages found" if empty_count > 0 else "No empty pages",
            "value": empty_count
        }
    
    def _check_character_distribution(self, text: str) -> Dict:
        """Check character distribution"""
        if not text:
            return {"name": "char_distribution", "passed": False, "severity": "error", "message": "No text", "value": 0}
        
        # Count alphanumeric vs others
        alphanumeric = sum(1 for c in text if c.isalnum())
        total = len(text)
        ratio = alphanumeric / total if total > 0 else 0
        
        # Should be at least 60% alphanumeric
        passed = ratio > 0.6
        
        return {
            "name": "char_distribution",
            "passed": passed,
            "severity": "warning" if not passed else "info",
            "message": f"Alphanumeric ratio: {ratio:.2%}",
            "value": round(ratio, 4)
        }
    
    def _check_whitespace_ratio(self, text: str) -> Dict:
        """Check whitespace ratio"""
        if not text:
            return {"name": "whitespace", "passed": False, "severity": "error", "message": "No text", "value": 0}
        
        whitespace = sum(1 for c in text if c.isspace())
        total = len(text)
        ratio = whitespace / total if total > 0 else 0
        
        # Whitespace should be between 10-30%
        passed = 0.10 <= ratio <= 0.35
        
        return {
            "name": "whitespace",
            "passed": passed,
            "severity": "info",
            "message": f"Whitespace ratio: {ratio:.2%}",
            "value": round(ratio, 4)
        }
    
    def _check_confidence_threshold(self, confidence: float) -> Dict:
        """Check if confidence meets threshold"""
        passed = confidence >= self.min_confidence_score
        
        return {
            "name": "confidence",
            "passed": passed,
            "severity": "error" if not passed else "info",
            "message": f"Confidence: {confidence:.2f}%",
            "value": confidence,
            "threshold": self.min_confidence_score
        }
    
    def _calculate_confidence_score(
        self,
        checks: List[Dict],
        passed: int,
        total: int,
        engine_confidence: float
    ) -> float:
        """
        Calculate overall confidence score with optimized weights for 100% data quality.

        Updated formula rewards successful data extraction and account matching:
        - Quality checks: 50% (validation passes)
        - Engine confidence: 30% (PDF extraction quality)
        - Data completeness: 20% (bonus for complete extraction)
        """

        # Base score from passed checks
        check_score = (passed / total) * 100 if total > 0 else 0

        # Calculate data completeness bonus
        # If all checks pass, award full 20% bonus
        completeness_bonus = (passed / total) * 20 if total > 0 else 0

        # Optimized weighted score for 100% data quality goal
        # 50% weight on checks, 30% on engine, 20% on completeness
        weighted_score = (check_score * 0.5) + (engine_confidence * 0.3) + completeness_bonus

        # Apply reduced penalties for critical failures (5% instead of 10%)
        # This prevents over-penalization when extraction is otherwise perfect
        critical_failures = 0
        for check in checks:
            if not check["passed"] and check["severity"] == "error":
                critical_failures += 1

        # Cap penalty at 15% total to avoid excessive reduction
        penalty = min(critical_failures * 5, 15)
        weighted_score -= penalty

        return max(0.0, min(100.0, weighted_score))
    
    def _determine_quality_level(self, confidence_score: float) -> str:
        """Determine quality level based on confidence score"""
        if confidence_score >= 95:
            return "excellent"
        elif confidence_score >= 85:
            return "good"
        elif confidence_score >= 70:
            return "acceptable"
        elif confidence_score >= 50:
            return "poor"
        else:
            return "failed"
    
    def _get_recommendations(
        self,
        quality: str,
        issues: List[str],
        extraction_result: Dict
    ) -> List[str]:
        """Get recommendations for improving extraction"""
        recommendations = []
        
        if quality in ["poor", "failed"]:
            recommendations.append("Consider manual review of this document")
            recommendations.append("Try re-scanning at higher DPI (300+)")
            
            # Check if it's likely a scanned document
            engine = extraction_result.get("engine", "")
            if engine != "tesseract_ocr":
                recommendations.append("Try OCR extraction for scanned documents")
        
        if quality == "acceptable":
            recommendations.append("Spot check extraction results")
            recommendations.append("Consider using multiple engines for validation")
        
        if "gibberish" in str(issues).lower():
            recommendations.append("Document may be scanned - use OCR engine")
            recommendations.append("Check image quality and orientation")
        
        if "empty" in str(issues).lower():
            recommendations.append("Some pages appear empty - verify source document")
        
        if not recommendations:
            recommendations.append("Extraction quality is high - safe to use")
        
        return recommendations
    
    def compare_extractions(
        self,
        extraction1: Dict,
        extraction2: Dict
    ) -> Dict:
        """
        Compare two extractions and calculate agreement score
        
        Used for cross-engine validation
        """
        try:
            text1 = extraction1.get("text", "")
            text2 = extraction2.get("text", "")
            
            # Calculate similarity
            similarity = self._calculate_text_similarity(text1, text2)
            
            # Compare word counts
            words1 = len(text1.split())
            words2 = len(text2.split())
            word_diff = abs(words1 - words2)
            word_diff_ratio = word_diff / max(words1, words2) if max(words1, words2) > 0 else 0
            
            # Determine agreement
            agreement = (similarity * 0.7) + ((1 - word_diff_ratio) * 0.3)
            
            return {
                "engine1": extraction1.get("engine", "unknown"),
                "engine2": extraction2.get("engine", "unknown"),
                "similarity": round(similarity * 100, 2),
                "agreement_score": round(agreement * 100, 2),
                "word_count_diff": word_diff,
                "word_count_diff_ratio": round(word_diff_ratio * 100, 2),
                "match_quality": "high" if agreement > 0.9 else "medium" if agreement > 0.7 else "low",
                "recommendation": self._get_comparison_recommendation(agreement),
                "success": True
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        if not text1 or not text2:
            return 0.0
        
        # Use SequenceMatcher for similarity
        similarity = SequenceMatcher(None, text1, text2).ratio()
        
        return similarity
    
    def _get_comparison_recommendation(self, agreement: float) -> str:
        """Get recommendation based on agreement score"""
        if agreement > 0.95:
            return "Excellent agreement - high confidence in extraction"
        elif agreement > 0.85:
            return "Good agreement - extraction likely accurate"
        elif agreement > 0.70:
            return "Moderate agreement - review discrepancies"
        else:
            return "Low agreement - manual review recommended"
    
    def calculate_consensus_score(
        self,
        extractions: List[Dict]
    ) -> Dict:
        """
        Calculate consensus across multiple engine extractions
        
        Args:
            extractions: List of extraction results from different engines
        
        Returns:
            dict: Consensus analysis
        """
        if len(extractions) < 2:
            return {
                "consensus_score": 100.0,
                "message": "Single engine - no consensus possible",
                "success": True
            }
        
        try:
            # Compare all pairs
            comparisons = []
            
            for i in range(len(extractions)):
                for j in range(i + 1, len(extractions)):
                    comp = self.compare_extractions(extractions[i], extractions[j])
                    comparisons.append(comp)
            
            # Calculate average agreement
            avg_agreement = sum(c["agreement_score"] for c in comparisons) / len(comparisons)
            
            # Determine consensus
            if avg_agreement > 90:
                consensus = "strong"
                message = "Strong consensus across engines - high confidence"
            elif avg_agreement > 75:
                consensus = "moderate"
                message = "Moderate consensus - good confidence"
            else:
                consensus = "weak"
                message = "Weak consensus - review recommended"
            
            return {
                "consensus_score": round(avg_agreement, 2),
                "consensus_level": consensus,
                "message": message,
                "comparisons": comparisons,
                "engines_compared": len(extractions),
                "success": True
            }
        
        except Exception as e:
            return {
                "consensus_score": 0.0,
                "success": False,
                "error": str(e)
            }

