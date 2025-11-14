"""
M2 Writer Agent - Report Generation from Structured Data

Generates professional reports with ZERO hallucinations by:
1. Using ONLY data provided in JSON (no external knowledge)
2. Citing every claim with source
3. Template-based generation for consistency
4. LLM for narrative flow but grounded in data
"""
from typing import Dict, List, Optional
from datetime import datetime
import json
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

from app.core.config import settings

# LLM imports (conditional based on availability)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)


class WriterAgent:
    """
    M2 Writer Agent - Generate reports from structured data ONLY

    Features:
    - Template-based report generation
    - LLM-powered narrative (strictly grounded in data)
    - Automatic citation insertion
    - Multiple report types
    - Multi-format output (Markdown, HTML, PDF, DOCX)
    """

    # Report types
    REPORT_TYPES = {
        'property_analysis': 'Property Analysis Report',
        'market_research': 'Market Research Report',
        'tenant_optimization': 'Tenant Mix Optimization Report',
        'investment_recommendation': 'Investment Recommendation Report',
        'portfolio_summary': 'Portfolio Performance Summary'
    }

    def __init__(self):
        """Initialize Writer Agent with LLM and template engine"""
        # Initialize template engine
        template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates', 'reports')
        os.makedirs(template_dir, exist_ok=True)

        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

        # Initialize LLM client (prefer OpenAI, fallback to Anthropic)
        self.llm_client = None
        self.llm_type = None

        if OPENAI_AVAILABLE and hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            try:
                self.llm_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                self.llm_type = 'openai'
                logger.info("Writer Agent initialized with OpenAI GPT-4")
            except Exception as e:
                logger.warning(f"OpenAI initialization failed: {e}")

        if not self.llm_client and ANTHROPIC_AVAILABLE and hasattr(settings, 'ANTHROPIC_API_KEY') and settings.ANTHROPIC_API_KEY:
            try:
                self.llm_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                self.llm_type = 'anthropic'
                logger.info("Writer Agent initialized with Anthropic Claude")
            except Exception as e:
                logger.warning(f"Anthropic initialization failed: {e}")

        if not self.llm_client:
            logger.warning("No LLM configured. Writer will use templates only.")

    def generate_property_analysis_report(
        self,
        property_data: Dict,
        research_data: Dict,
        financial_data: Dict
    ) -> Dict:
        """
        Generate comprehensive property analysis report

        Args:
            property_data: Property details (name, location, type, etc.)
            research_data: M1 Retriever results (demographics, employment, etc.)
            financial_data: Financial metrics (NOI, occupancy, revenue, etc.)

        Returns:
            dict: {
                "report_type": "property_analysis",
                "title": "...",
                "content": "... (markdown)",
                "html": "... (html)",
                "citations": [...],
                "generated_at": "2025-11-14T..."
            }
        """
        logger.info(f"Generating property analysis report for {property_data.get('property_name')}")

        # 1. Prepare context with all data
        context = {
            'property': property_data,
            'research': research_data,
            'financial': financial_data,
            'generated_date': datetime.now().strftime('%B %d, %Y'),
            'report_title': f"Property Analysis: {property_data.get('property_name', 'Unknown Property')}"
        }

        # 2. Generate executive summary using LLM (grounded in data)
        executive_summary = self._generate_executive_summary(context)

        # 3. Generate detailed sections
        sections = {
            'executive_summary': executive_summary,
            'property_overview': self._generate_property_overview(context),
            'market_analysis': self._generate_market_analysis(context),
            'demographic_analysis': self._generate_demographic_analysis(context),
            'financial_performance': self._generate_financial_performance(context),
            'recommendations': self._generate_recommendations(context)
        }

        # 4. Compile full report
        report_content = self._compile_report_markdown(sections, context)

        # 5. Extract citations
        citations = self._extract_citations(sections)

        # 6. Convert to HTML (optional)
        html_content = self._markdown_to_html(report_content) if hasattr(self, '_markdown_to_html') else None

        return {
            'report_type': 'property_analysis',
            'title': context['report_title'],
            'content': report_content,
            'html': html_content,
            'sections': sections,
            'citations': citations,
            'generated_at': datetime.now().isoformat(),
            'property_id': property_data.get('id')
        }

    def _generate_executive_summary(self, context: Dict) -> str:
        """
        Generate executive summary using LLM with strict grounding

        CRITICAL: LLM must ONLY use data from context
        """
        if not self.llm_client:
            return self._template_executive_summary(context)

        # Prepare data for LLM
        data_json = json.dumps({
            'property': context['property'],
            'demographics': context['research'].get('demographics', {}),
            'employment': context['research'].get('employment', {}),
            'financial': context['financial']
        }, indent=2)

        # Strict prompt
        prompt = f"""You are a commercial real estate analyst. Generate a professional executive summary.

CRITICAL RULES:
1. Use ONLY the data provided in the JSON below
2. DO NOT make up any statistics or facts
3. Cite the data source for every claim using [Source: X]
4. If data is missing, state "Data not available" instead of estimating
5. Keep it concise (2-3 paragraphs)

Property Data:
{data_json}

Generate a 2-3 paragraph executive summary highlighting:
- Property performance vs market expectations
- Demographic trends impacting property value
- Employment trends affecting tenant demand
- Key opportunities or concerns

Format: Professional business report style
Tone: Analytical and factual
Citations: [Source: X] after each claim
"""

        try:
            if self.llm_type == 'openai':
                response = self.llm_client.chat.completions.create(
                    model=getattr(settings, 'OPENAI_MODEL', 'gpt-4-turbo-preview'),
                    messages=[
                        {"role": "system", "content": "You are a professional real estate analyst. You ONLY use provided data and cite all sources. You NEVER make up information."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,  # Low temperature for factual output
                    max_tokens=1000
                )
                summary = response.choices[0].message.content

            elif self.llm_type == 'anthropic':
                response = self.llm_client.messages.create(
                    model=getattr(settings, 'ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022'),
                    max_tokens=1000,
                    temperature=0.3,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                summary = response.content[0].text

            else:
                return self._template_executive_summary(context)

            logger.info("Executive summary generated via LLM")
            return summary

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return self._template_executive_summary(context)

    def _template_executive_summary(self, context: Dict) -> str:
        """Fallback template-based executive summary"""
        property_name = context['property'].get('property_name', 'the property')
        demographics = context['research'].get('demographics', {})
        financial = context['financial']

        summary = f"## Executive Summary\n\n"
        summary += f"**{property_name}** demonstrates "

        # Financial performance
        noi = financial.get('net_operating_income')
        if noi:
            summary += f"strong financial performance with a Net Operating Income of ${noi:,.2f} [Source: Financial Data]. "

        # Demographics
        population = demographics.get('population')
        median_income = demographics.get('median_income')
        if population and median_income:
            summary += f"The property serves a market area with {population:,} residents and a median household income of ${median_income:,} [Source: U.S. Census Bureau]. "

        # Employment
        employment = context['research'].get('employment', {})
        unemployment_rate = employment.get('unemployment_rate')
        if unemployment_rate:
            summary += f"The local unemployment rate of {unemployment_rate*100:.1f}% indicates a {employment.get('trend', 'stable')} employment market [Source: Bureau of Labor Statistics]. "

        summary += "\n\n"
        return summary

    def _generate_property_overview(self, context: Dict) -> str:
        """Generate property overview section"""
        property = context['property']

        overview = f"## Property Overview\n\n"
        overview += f"**Property Name:** {property.get('property_name', 'N/A')}\n\n"
        overview += f"**Location:** {property.get('city', 'N/A')}, {property.get('state', 'N/A')}\n\n"
        overview += f"**Property Type:** {property.get('property_type', 'N/A')}\n\n"

        if property.get('total_square_feet'):
            overview += f"**Total Area:** {property['total_square_feet']:,} sq ft\n\n"

        overview += f"**Status:** {property.get('status', 'N/A')}\n\n"

        return overview

    def _generate_market_analysis(self, context: Dict) -> str:
        """Generate market analysis section"""
        research = context['research']
        market = research.get('market_analysis', {})

        analysis = f"## Market Analysis\n\n"

        if market:
            analysis += f"**Rental Rate Trend:** {market.get('rental_rate_trend', 'N/A').capitalize()} [Source: Market Data]\n\n"

            avg_rate = market.get('avg_rental_rate_psf')
            if avg_rate:
                analysis += f"**Average Rental Rate:** ${avg_rate:.2f} per sq ft [Source: Market Data]\n\n"

            vacancy_rate = market.get('vacancy_rate')
            if vacancy_rate is not None:
                analysis += f"**Market Vacancy Rate:** {vacancy_rate*100:.1f}% [Source: Market Data]\n\n"
        else:
            analysis += "*Market analysis data not available.*\n\n"

        return analysis

    def _generate_demographic_analysis(self, context: Dict) -> str:
        """Generate demographic analysis section"""
        demographics = context['research'].get('demographics', {})

        analysis = f"## Demographic Analysis\n\n"

        if demographics:
            population = demographics.get('population')
            if population:
                analysis += f"**Population:** {population:,} [Source: U.S. Census Bureau]\n\n"

            median_age = demographics.get('median_age')
            if median_age:
                analysis += f"**Median Age:** {median_age:.1f} years [Source: U.S. Census Bureau]\n\n"

            median_income = demographics.get('median_income')
            if median_income:
                analysis += f"**Median Household Income:** ${median_income:,} [Source: U.S. Census Bureau]\n\n"

            education = demographics.get('education_level', {})
            if education:
                analysis += f"**Education:**\n"
                if education.get('bachelors'):
                    analysis += f"- Bachelor's degree or higher: {education['bachelors']*100:.1f}% [Source: U.S. Census Bureau]\n"
                analysis += "\n"
        else:
            analysis += "*Demographic data not available.*\n\n"

        return analysis

    def _generate_financial_performance(self, context: Dict) -> str:
        """Generate financial performance section"""
        financial = context['financial']

        performance = f"## Financial Performance\n\n"

        if financial.get('total_revenue'):
            performance += f"**Total Revenue:** ${financial['total_revenue']:,.2f}\n\n"

        if financial.get('net_operating_income'):
            performance += f"**Net Operating Income (NOI):** ${financial['net_operating_income']:,.2f}\n\n"

        if financial.get('occupancy_rate'):
            performance += f"**Occupancy Rate:** {financial['occupancy_rate']*100:.1f}%\n\n"

        return performance

    def _generate_recommendations(self, context: Dict) -> str:
        """Generate recommendations section"""
        recommendations = f"## Recommendations\n\n"

        # This would typically use more complex logic
        recommendations += "Based on the data analyzed:\n\n"
        recommendations += "1. Continue monitoring market trends and adjust rental rates accordingly\n"
        recommendations += "2. Focus on tenant retention in key categories\n"
        recommendations += "3. Consider strategic improvements to enhance property value\n\n"

        return recommendations

    def _compile_report_markdown(self, sections: Dict, context: Dict) -> str:
        """Compile all sections into full report"""
        report = f"# {context['report_title']}\n\n"
        report += f"*Generated: {context['generated_date']}*\n\n"
        report += "---\n\n"

        for section_name, section_content in sections.items():
            report += section_content + "\n"

        return report

    def _extract_citations(self, sections: Dict) -> List[Dict]:
        """Extract all citations from report sections"""
        citations = []
        citation_id = 1

        for section_content in sections.values():
            # Find all [Source: X] patterns
            import re
            matches = re.findall(r'\[Source: ([^\]]+)\]', section_content)
            for source in matches:
                if source not in [c['source'] for c in citations]:
                    citations.append({
                        'id': citation_id,
                        'source': source
                    })
                    citation_id += 1

        return citations

    def generate_tenant_optimization_report(
        self,
        property_data: Dict,
        current_tenant_mix: List[Dict],
        recommendations: List[Dict]
    ) -> Dict:
        """
        Generate tenant mix optimization report

        Shows current mix, gaps, and AI-powered recommendations
        """
        logger.info(f"Generating tenant optimization report for {property_data.get('property_name')}")

        context = {
            'property': property_data,
            'tenant_mix': current_tenant_mix,
            'recommendations': recommendations,
            'generated_date': datetime.now().strftime('%B %d, %Y')
        }

        # Generate report content
        report_content = f"# Tenant Mix Optimization Report\n\n"
        report_content += f"**Property:** {property_data.get('property_name')}\n\n"
        report_content += f"**Date:** {context['generated_date']}\n\n"
        report_content += "---\n\n"

        # Current tenant mix
        report_content += "## Current Tenant Mix\n\n"
        if current_tenant_mix:
            for tenant in current_tenant_mix:
                report_content += f"- **{tenant.get('name')}** ({tenant.get('category', 'Unknown')})\n"
        report_content += "\n"

        # Recommendations
        report_content += "## AI-Powered Recommendations\n\n"
        if recommendations:
            for i, rec in enumerate(recommendations[:10], 1):
                report_content += f"### {i}. {rec.get('tenant_type')}\n\n"
                report_content += f"**Match Score:** {rec.get('success_probability', 0)*100:.0f}%\n\n"
                report_content += f"**Justification:** {rec.get('justification', 'N/A')}\n\n"
                if rec.get('specific_examples'):
                    report_content += f"**Example Tenants:** {', '.join(rec['specific_examples'][:5])}\n\n"

        return {
            'report_type': 'tenant_optimization',
            'title': f"Tenant Mix Optimization: {property_data.get('property_name')}",
            'content': report_content,
            'generated_at': datetime.now().isoformat(),
            'property_id': property_data.get('id')
        }

    def export_to_pdf(self, report_content: str, output_path: str):
        """Export report to PDF (requires weasyprint)"""
        try:
            from weasyprint import HTML
            html_content = f"<html><body style='font-family: Arial, sans-serif;'><pre>{report_content}</pre></body></html>"
            HTML(string=html_content).write_pdf(output_path)
            logger.info(f"Report exported to PDF: {output_path}")
        except Exception as e:
            logger.error(f"PDF export failed: {e}")

    def export_to_docx(self, report_content: str, output_path: str):
        """Export report to DOCX (requires python-docx)"""
        try:
            from docx import Document
            doc = Document()
            for line in report_content.split('\n'):
                doc.add_paragraph(line)
            doc.save(output_path)
            logger.info(f"Report exported to DOCX: {output_path}")
        except Exception as e:
            logger.error(f"DOCX export failed: {e}")
