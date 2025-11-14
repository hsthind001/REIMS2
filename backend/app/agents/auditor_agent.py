"""
M3 Auditor Agent - Report Verification & Hallucination Detection

Verifies every claim in generated reports line-by-line:
1. Factual verification (numbers match source data)
2. Citation validation (every claim is cited)
3. Consistency checks (no contradictions)
4. Hallucination detection (flag unsupported claims)
"""
from typing import Dict, List, Optional, Tuple
import re
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AuditorAgent:
    """
    M3 Auditor Agent - Verify claims and detect hallucinations

    Quality checks:
    - Factual accuracy: Do numbers match source data?
    - Citation coverage: Is every claim cited?
    - Consistency: Are there contradictions?
    - Hallucinations: Are there unsupported claims?
    """

    # Severity levels
    SEVERITY_CRITICAL = 'critical'
    SEVERITY_HIGH = 'high'
    SEVERITY_MEDIUM = 'medium'
    SEVERITY_LOW = 'low'

    # Issue types
    ISSUE_MISSING_CITATION = 'missing_citation'
    ISSUE_INCORRECT_VALUE = 'incorrect_value'
    ISSUE_UNSUPPORTED_CLAIM = 'unsupported_claim'
    ISSUE_SPECULATIVE_LANGUAGE = 'speculative_language'
    ISSUE_CONTRADICTION = 'contradiction'
    ISSUE_OUTDATED_DATA = 'outdated_data'

    def __init__(self):
        """Initialize Auditor Agent"""
        pass

    def audit_report(
        self,
        report_text: str,
        source_data: Dict,
        report_type: str = 'property_analysis'
    ) -> Dict:
        """
        Comprehensive audit of generated report

        Args:
            report_text: The generated report content (markdown)
            source_data: All source data used to generate report
            report_type: Type of report being audited

        Returns:
            dict: Audit results with issues, scores, and recommendations
        """
        logger.info(f"Starting audit of {report_type} report ({len(report_text)} chars)")

        # 1. Parse report into claims
        claims = self._extract_claims(report_text)
        logger.info(f"Extracted {len(claims)} claims from report")

        # 2. Verify each claim
        issues = []
        verified_claims = 0

        for claim in claims:
            claim_issues = self._verify_claim(claim, source_data)
            if not claim_issues:
                verified_claims += 1
            else:
                issues.extend(claim_issues)

        # 3. Check citation coverage
        citation_issues = self._check_citation_coverage(report_text, claims)
        issues.extend(citation_issues)

        # 4. Detect contradictions
        contradiction_issues = self._detect_contradictions(claims, source_data)
        issues.extend(contradiction_issues)

        # 5. Detect speculative language
        speculative_issues = self._detect_speculative_language(report_text)
        issues.extend(speculative_issues)

        # 6. Calculate scores
        scores = self._calculate_quality_scores(
            len(claims),
            verified_claims,
            len(issues),
            report_text
        )

        # 7. Determine overall status
        validation_status = self._determine_validation_status(issues, scores)

        # 8. Generate recommendations
        recommendations = self._generate_recommendations(issues, scores)

        audit_result = {
            'validation_status': validation_status,
            'total_claims': len(claims),
            'verified_claims': verified_claims,
            'issues_found': issues,
            'issue_count_by_severity': {
                self.SEVERITY_CRITICAL: sum(1 for i in issues if i['severity'] == self.SEVERITY_CRITICAL),
                self.SEVERITY_HIGH: sum(1 for i in issues if i['severity'] == self.SEVERITY_HIGH),
                self.SEVERITY_MEDIUM: sum(1 for i in issues if i['severity'] == self.SEVERITY_MEDIUM),
                self.SEVERITY_LOW: sum(1 for i in issues if i['severity'] == self.SEVERITY_LOW),
            },
            'scores': scores,
            'recommendations': recommendations,
            'audit_date': datetime.now().isoformat(),
            'audited_by': 'M3-Auditor',
            'report_type': report_type
        }

        logger.info(f"Audit complete. Status: {validation_status}, Factual accuracy: {scores['factual_accuracy']:.2%}")

        return audit_result

    def _extract_claims(self, report_text: str) -> List[Dict]:
        """
        Extract all factual claims from report

        A claim is:
        - A sentence with a number/statistic
        - An assertion about property/market
        - A recommendation or conclusion
        """
        claims = []
        claim_id = 1

        # Split into sentences
        sentences = re.split(r'[.!?]\s+', report_text)

        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue

            # Check if sentence contains a factual claim
            has_number = bool(re.search(r'\d+', sentence))
            has_citation = bool(re.search(r'\[Source:', sentence))
            is_header = sentence.startswith('#')

            if (has_number or 'trend' in sentence.lower() or 'rate' in sentence.lower()) and not is_header:
                # Extract numbers
                numbers = re.findall(r'[\d,]+\.?\d*', sentence)

                claim = {
                    'id': claim_id,
                    'text': sentence,
                    'line_number': i + 1,
                    'has_citation': has_citation,
                    'numbers': [n.replace(',', '') for n in numbers],
                    'type': 'quantitative' if has_number else 'qualitative'
                }
                claims.append(claim)
                claim_id += 1

        return claims

    def _verify_claim(self, claim: Dict, source_data: Dict) -> List[Dict]:
        """
        Verify a single claim against source data

        Returns list of issues found (empty if claim is valid)
        """
        issues = []

        # Skip non-quantitative claims for now (harder to verify)
        if claim['type'] != 'quantitative' or not claim['numbers']:
            return issues

        # Extract numbers from claim
        claim_numbers = claim['numbers']

        # Search for these numbers in source data
        found_in_source = False
        for number in claim_numbers:
            if self._number_exists_in_data(float(number), source_data):
                found_in_source = True
                break

        if not found_in_source and claim['numbers']:
            # Number not found in source data - potential hallucination
            issues.append({
                'severity': self.SEVERITY_HIGH,
                'type': self.ISSUE_INCORRECT_VALUE,
                'line_number': claim['line_number'],
                'text': claim['text'],
                'issue': f"Number(s) {claim['numbers']} not found in source data",
                'suggested_fix': "Verify this number against source data or remove the claim"
            })

        return issues

    def _number_exists_in_data(self, number: float, data: Dict, tolerance: float = 0.01) -> bool:
        """
        Check if a number exists anywhere in nested source data

        Uses recursive search with tolerance for floating point comparison
        """
        def search_recursive(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    if search_recursive(value):
                        return True
            elif isinstance(obj, list):
                for item in obj:
                    if search_recursive(item):
                        return True
            elif isinstance(obj, (int, float)):
                # Compare with tolerance
                if abs(float(obj) - number) / max(abs(number), 1) < tolerance:
                    return True
            elif isinstance(obj, str):
                # Try to extract numbers from string
                try:
                    extracted = float(obj.replace(',', ''))
                    if abs(extracted - number) / max(abs(number), 1) < tolerance:
                        return True
                except (ValueError, AttributeError):
                    pass
            return False

        return search_recursive(data)

    def _check_citation_coverage(self, report_text: str, claims: List[Dict]) -> List[Dict]:
        """
        Check that all claims have proper citations

        Every factual claim should have a [Source: X] citation
        """
        issues = []

        for claim in claims:
            if claim['type'] == 'quantitative' and not claim['has_citation']:
                issues.append({
                    'severity': self.SEVERITY_MEDIUM,
                    'type': self.ISSUE_MISSING_CITATION,
                    'line_number': claim['line_number'],
                    'text': claim['text'],
                    'issue': 'Quantitative claim without citation',
                    'suggested_fix': 'Add [Source: X] citation to support this claim'
                })

        return issues

    def _detect_contradictions(self, claims: List[Dict], source_data: Dict) -> List[Dict]:
        """
        Detect contradictory claims in the report

        For example:
        - "Population is increasing" vs "Population is decreasing"
        - Inconsistent numbers for same metric
        """
        issues = []

        # This is a simplified version - real implementation would use NLP
        # to detect semantic contradictions

        # Check for numerical contradictions
        number_claims = {}  # {context: [numbers]}

        for claim in claims:
            if not claim['numbers']:
                continue

            # Extract context (simplified - look for keywords before number)
            text_lower = claim['text'].lower()

            for keyword in ['population', 'income', 'rate', 'revenue', 'noi', 'occupancy']:
                if keyword in text_lower:
                    if keyword not in number_claims:
                        number_claims[keyword] = []
                    number_claims[keyword].extend(claim['numbers'])

        # Check for significantly different numbers for same metric
        for context, numbers in number_claims.items():
            if len(numbers) > 1:
                # Convert to floats
                try:
                    nums = [float(n.replace(',', '')) for n in numbers]
                    # Check if numbers vary significantly
                    if max(nums) / min(nums) > 1.5:  # 50% difference
                        issues.append({
                            'severity': self.SEVERITY_MEDIUM,
                            'type': self.ISSUE_CONTRADICTION,
                            'line_number': None,
                            'text': None,
                            'issue': f"Contradictory numbers for '{context}': {numbers}",
                            'suggested_fix': 'Verify which number is correct and ensure consistency'
                        })
                except (ValueError, ZeroDivisionError):
                    pass

        return issues

    def _detect_speculative_language(self, report_text: str) -> List[Dict]:
        """
        Detect speculative or hedging language that needs caveats

        Phrases like:
        - "will likely", "probably", "may", "could"
        - Without proper caveats
        """
        issues = []

        speculative_patterns = [
            r'will likely',
            r'\bprobably\b',
            r'\bmay\b(?! \d)',  # "may" not followed by number (May = month)
            r'\bcould\b',
            r'\bshould\b',
            r'is expected to',
            r'appears to',
        ]

        caveat_phrases = [
            'based on current data',
            'historical trends suggest',
            'if trends continue',
            'assuming',
        ]

        sentences = re.split(r'[.!?]\s+', report_text)

        for i, sentence in enumerate(sentences):
            # Check for speculative language
            has_speculation = any(re.search(pattern, sentence, re.IGNORECASE) for pattern in speculative_patterns)

            if has_speculation:
                # Check if sentence has caveats
                has_caveat = any(phrase.lower() in sentence.lower() for phrase in caveat_phrases)

                if not has_caveat:
                    issues.append({
                        'severity': self.SEVERITY_LOW,
                        'type': self.ISSUE_SPECULATIVE_LANGUAGE,
                        'line_number': i + 1,
                        'text': sentence,
                        'issue': 'Speculative claim without proper caveat',
                        'suggested_fix': 'Add qualifier like "Based on current data, ..." or "Historical trends suggest..."'
                    })

        return issues

    def _calculate_quality_scores(
        self,
        total_claims: int,
        verified_claims: int,
        total_issues: int,
        report_text: str
    ) -> Dict[str, float]:
        """
        Calculate quality scores

        Scores:
        - factual_accuracy: % of claims verified against source data
        - citation_coverage: % of claims with proper citations
        - hallucination_score: % of potential hallucinations
        - overall_quality: Weighted average
        """
        if total_claims == 0:
            return {
                'factual_accuracy': 1.0,
                'citation_coverage': 1.0,
                'hallucination_score': 0.0,
                'overall_quality': 'A'
            }

        # Factual accuracy
        factual_accuracy = verified_claims / total_claims if total_claims > 0 else 1.0

        # Citation coverage
        citations = re.findall(r'\[Source:', report_text)
        citation_coverage = min(1.0, len(citations) / total_claims)

        # Hallucination score (inverse of accuracy)
        hallucination_score = 1.0 - factual_accuracy

        # Overall quality (letter grade)
        overall_score = (factual_accuracy * 0.5 + citation_coverage * 0.3 + (1 - hallucination_score) * 0.2)

        if overall_score >= 0.95:
            quality_grade = 'A+'
        elif overall_score >= 0.90:
            quality_grade = 'A'
        elif overall_score >= 0.85:
            quality_grade = 'A-'
        elif overall_score >= 0.80:
            quality_grade = 'B+'
        elif overall_score >= 0.75:
            quality_grade = 'B'
        elif overall_score >= 0.70:
            quality_grade = 'B-'
        else:
            quality_grade = 'C'

        return {
            'factual_accuracy': factual_accuracy,
            'citation_coverage': citation_coverage,
            'hallucination_score': hallucination_score,
            'overall_score': overall_score,
            'overall_quality': quality_grade
        }

    def _determine_validation_status(self, issues: List[Dict], scores: Dict) -> str:
        """
        Determine overall validation status

        Statuses:
        - passed: No critical issues, high scores
        - passed_with_warnings: Minor issues, acceptable scores
        - needs_revision: Multiple medium/high issues
        - failed: Critical issues or low scores
        """
        critical_issues = sum(1 for i in issues if i['severity'] == self.SEVERITY_CRITICAL)
        high_issues = sum(1 for i in issues if i['severity'] == self.SEVERITY_HIGH)

        factual_accuracy = scores.get('factual_accuracy', 0)

        if critical_issues > 0 or factual_accuracy < 0.80:
            return 'failed'
        elif high_issues > 2 or factual_accuracy < 0.90:
            return 'needs_revision'
        elif len(issues) > 0:
            return 'passed_with_warnings'
        else:
            return 'passed'

    def _generate_recommendations(self, issues: List[Dict], scores: Dict) -> List[str]:
        """Generate recommendations based on audit results"""
        recommendations = []

        critical_issues = sum(1 for i in issues if i['severity'] == self.SEVERITY_CRITICAL)
        high_issues = sum(1 for i in issues if i['severity'] == self.SEVERITY_HIGH)

        if critical_issues > 0:
            recommendations.append(f"CRITICAL: {critical_issues} critical issue(s) must be fixed before approval")

        if high_issues > 0:
            recommendations.append(f"HIGH: {high_issues} high-severity issue(s) should be addressed")

        if scores.get('factual_accuracy', 1) < 0.90:
            recommendations.append("Improve factual accuracy by verifying all numbers against source data")

        if scores.get('citation_coverage', 1) < 0.80:
            recommendations.append("Add more citations to support claims")

        missing_citation_count = sum(1 for i in issues if i['type'] == self.ISSUE_MISSING_CITATION)
        if missing_citation_count > 0:
            recommendations.append(f"Add citations to {missing_citation_count} claims")

        speculative_count = sum(1 for i in issues if i['type'] == self.ISSUE_SPECULATIVE_LANGUAGE)
        if speculative_count > 0:
            recommendations.append(f"Add caveats to {speculative_count} speculative statements")

        if not recommendations:
            recommendations.append("Report meets quality standards")

        return recommendations

    def export_audit_report(self, audit_result: Dict) -> str:
        """
        Export audit results as formatted report

        Returns markdown-formatted audit report
        """
        report = "# Report Audit Results\n\n"
        report += f"**Status:** {audit_result['validation_status'].upper()}\n\n"
        report += f"**Overall Quality:** {audit_result['scores']['overall_quality']}\n\n"
        report += f"**Audit Date:** {audit_result['audit_date']}\n\n"
        report += "---\n\n"

        # Scores
        report += "## Quality Scores\n\n"
        scores = audit_result['scores']
        report += f"- **Factual Accuracy:** {scores['factual_accuracy']:.1%}\n"
        report += f"- **Citation Coverage:** {scores['citation_coverage']:.1%}\n"
        report += f"- **Hallucination Score:** {scores['hallucination_score']:.1%}\n\n"

        # Issues summary
        report += "## Issues Found\n\n"
        issue_counts = audit_result['issue_count_by_severity']
        report += f"- **Critical:** {issue_counts[self.SEVERITY_CRITICAL]}\n"
        report += f"- **High:** {issue_counts[self.SEVERITY_HIGH]}\n"
        report += f"- **Medium:** {issue_counts[self.SEVERITY_MEDIUM]}\n"
        report += f"- **Low:** {issue_counts[self.SEVERITY_LOW]}\n\n"

        # Detailed issues
        if audit_result['issues_found']:
            report += "## Detailed Issues\n\n"
            for i, issue in enumerate(audit_result['issues_found'][:20], 1):  # Show first 20
                report += f"### Issue {i} - {issue['type'].replace('_', ' ').title()}\n\n"
                report += f"**Severity:** {issue['severity'].upper()}\n\n"
                if issue.get('line_number'):
                    report += f"**Line:** {issue['line_number']}\n\n"
                if issue.get('text'):
                    report += f"**Text:** {issue['text']}\n\n"
                report += f"**Issue:** {issue['issue']}\n\n"
                report += f"**Suggested Fix:** {issue['suggested_fix']}\n\n"

        # Recommendations
        report += "## Recommendations\n\n"
        for i, rec in enumerate(audit_result['recommendations'], 1):
            report += f"{i}. {rec}\n"

        return report
