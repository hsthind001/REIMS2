
import logging
import base64
import io
from typing import Dict, Any, List, Optional
from pdf2image import convert_from_bytes
from app.services.local_llm_service import get_local_llm_service

logger = logging.getLogger(__name__)

class ImageAnalysisService:
    """
    Service for Visual Understanding of financial documents.
    Uses LLaVA (via LocalLLMService) to analyze charts, graphs, and visual layouts.
    """

    def __init__(self):
        self.llm_service = get_local_llm_service()

    async def analyze_pdf_page(
        self, 
        pdf_content: bytes, 
        page_number: int = 1,
        prompt: str = "Describe this image in detail."
    ) -> Dict[str, Any]:
        """
        Convert a specific PDF page to an image and analyze it with LLaVA.
        """
        try:
            # Convert PDF bytes to image (first page by default)
            # fmt="jpeg" is faster and smaller for LLMs
            images = convert_from_bytes(
                pdf_content, 
                first_page=page_number, 
                last_page=page_number, 
                fmt="jpeg"
            )
            
            if not images:
                return {"error": "Could not convert PDF to image"}
            
            image = images[0]
            
            # Convert PIL image to base64 string
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # Format as data URI
            image_b64 = f"data:image/jpeg;base64,{img_str}"
            
            # Call LLM Service
            logger.info(f"Sending page {page_number} image to LLaVA for analysis...")
            description = await self.llm_service.analyze_image(
                image_b64=image_b64,
                prompt=prompt
            )
            
            return {
                "success": True,
                "page": page_number,
                "analysis": description
            }
            
        except ImportError:
            return {"error": "pdf2image or poppler not installed"}
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return {"success": False, "error": str(e)}

    async def extract_charts_and_graphs(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        Specifically look for and summarize charts/graphs in the document.
        """
        prompt = """
        Analyze this page for any charts, graphs, or visual trends.
        If found, summarize the key trend (e.g., "Revenue is increasing month-over-month").
        If no charts are found, simply reply "No charts found."
        """
        # Analyze first 3 pages (usually where higher level summaries are)
        results = []
        for i in range(1, 4):
            try:
                result = await self.analyze_pdf_page(pdf_content, page_number=i, prompt=prompt)
                if result.get("success") and "No charts found" not in result.get("analysis", ""):
                    results.append(result)
            except Exception:
                continue
                
        return {
            "success": True,
            "charts_found": len(results),
            "details": results
        }
