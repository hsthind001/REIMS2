"""
PDF Quality Enhancer - Preprocessing for optimal extraction

Improves PDF quality before extraction:
1. Image enhancement (denoise, contrast, deskew)
2. Layout analysis and correction
3. Quality scoring
4. Adaptive preprocessing based on quality
"""
import io
from typing import Dict, Tuple, Optional
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import cv2
from pdf2image import convert_from_bytes
from PyPDF2 import PdfReader, PdfWriter
import logging

logger = logging.getLogger(__name__)


class PDFQualityEnhancer:
    """
    Enhance PDF quality for better extraction accuracy

    Features:
    - Deskew pages
    - Enhance contrast
    - Denoise images
    - Binarization for OCR
    - Layout detection and correction
    """

    def __init__(self):
        self.dpi = 300  # DPI for image conversion

    def assess_quality(self, pdf_data: bytes) -> Dict[str, any]:
        """
        Assess PDF quality

        Returns quality score (0-1) and recommendations
        """
        try:
            # Convert first page to image
            images = convert_from_bytes(
                pdf_data,
                first_page=1,
                last_page=1,
                dpi=self.dpi
            )

            if not images:
                return {
                    "quality_score": 0.0,
                    "is_scanned": True,
                    "needs_enhancement": True,
                    "issues": ["Failed to convert PDF to image"]
                }

            img = images[0]
            img_array = np.array(img)

            # Analyze image quality
            is_scanned = self._detect_scanned_document(img_array)
            sharpness = self._measure_sharpness(img_array)
            contrast = self._measure_contrast(img_array)
            skew_angle = self._detect_skew(img_array)

            # Calculate overall quality score
            quality_score = self._calculate_quality_score(
                sharpness, contrast, abs(skew_angle)
            )

            issues = []
            if is_scanned:
                issues.append("Document appears to be scanned")
            if sharpness < 100:
                issues.append("Low sharpness detected")
            if contrast < 40:
                issues.append("Low contrast detected")
            if abs(skew_angle) > 1.0:
                issues.append(f"Document skewed by {skew_angle:.1f} degrees")

            return {
                "quality_score": quality_score,
                "is_scanned": is_scanned,
                "sharpness": sharpness,
                "contrast": contrast,
                "skew_angle": skew_angle,
                "needs_enhancement": quality_score < 0.7,
                "issues": issues
            }

        except Exception as e:
            logger.error(f"Quality assessment failed: {str(e)}")
            return {
                "quality_score": 0.5,  # Assume medium quality
                "is_scanned": False,
                "needs_enhancement": True,
                "issues": [f"Assessment error: {str(e)}"]
            }

    def enhance(self, pdf_data: bytes, quality_assessment: Optional[Dict] = None) -> bytes:
        """
        Enhance PDF quality

        Args:
            pdf_data: Original PDF bytes
            quality_assessment: Optional pre-computed quality assessment

        Returns:
            bytes: Enhanced PDF
        """
        if quality_assessment is None:
            quality_assessment = self.assess_quality(pdf_data)

        # If quality is already good, return original
        if quality_assessment['quality_score'] > 0.85:
            logger.info("PDF quality is already high, skipping enhancement")
            return pdf_data

        logger.info(f"Enhancing PDF (quality score: {quality_assessment['quality_score']:.2f})")

        try:
            # Convert all pages to images
            images = convert_from_bytes(pdf_data, dpi=self.dpi)

            enhanced_images = []
            for i, img in enumerate(images):
                logger.info(f"Enhancing page {i+1}/{len(images)}")
                enhanced_img = self._enhance_image(img, quality_assessment)
                enhanced_images.append(enhanced_img)

            # Convert enhanced images back to PDF
            enhanced_pdf = self._images_to_pdf(enhanced_images)

            logger.info("PDF enhancement complete")
            return enhanced_pdf

        except Exception as e:
            logger.error(f"PDF enhancement failed: {str(e)}")
            return pdf_data  # Return original on error

    def _enhance_image(self, img: Image.Image, quality_assessment: Dict) -> Image.Image:
        """
        Apply image enhancements

        Steps:
        1. Deskew if needed
        2. Enhance contrast
        3. Sharpen if blurry
        4. Denoise
        5. Binarize for OCR (optional)
        """
        img_array = np.array(img)

        # 1. Deskew
        if abs(quality_assessment.get('skew_angle', 0)) > 0.5:
            img_array = self._deskew_image(img_array, quality_assessment['skew_angle'])

        # 2. Enhance contrast
        if quality_assessment.get('contrast', 100) < 50:
            img_array = self._enhance_contrast(img_array)

        # 3. Sharpen if blurry
        if quality_assessment.get('sharpness', 100) < 100:
            img_array = self._sharpen_image(img_array)

        # 4. Denoise
        img_array = self._denoise_image(img_array)

        # 5. Convert back to PIL Image
        enhanced_img = Image.fromarray(img_array)

        return enhanced_img

    def _detect_scanned_document(self, img_array: np.ndarray) -> bool:
        """
        Detect if document is scanned (vs digitally created)

        Scanned documents typically have:
        - Higher noise levels
        - Inconsistent background
        - Artifacts from scanning
        """
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Calculate noise level (standard deviation of Laplacian)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Scanned documents typically have laplacian variance < 100
        is_scanned = laplacian_var < 100

        return is_scanned

    def _measure_sharpness(self, img_array: np.ndarray) -> float:
        """
        Measure image sharpness using variance of Laplacian

        Higher values = sharper image
        """
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        return float(laplacian_var)

    def _measure_contrast(self, img_array: np.ndarray) -> float:
        """
        Measure image contrast (0-100 scale)

        Uses standard deviation of pixel intensities
        """
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Calculate standard deviation (higher = more contrast)
        std_dev = np.std(gray)

        # Normalize to 0-100 scale (std_dev typically 0-128)
        contrast = min(100, (std_dev / 128.0) * 100)

        return float(contrast)

    def _detect_skew(self, img_array: np.ndarray) -> float:
        """
        Detect skew angle using Hough Line Transform

        Returns angle in degrees (-45 to 45)
        """
        try:
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array

            # Edge detection
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)

            # Hough Line Transform
            lines = cv2.HoughLines(edges, 1, np.pi/180, 200)

            if lines is None:
                return 0.0

            # Calculate most common angle
            angles = []
            for line in lines:
                rho, theta = line[0]
                angle = np.degrees(theta) - 90
                if -45 < angle < 45:
                    angles.append(angle)

            if not angles:
                return 0.0

            # Return median angle
            median_angle = np.median(angles)
            return float(median_angle)

        except Exception as e:
            logger.error(f"Skew detection failed: {str(e)}")
            return 0.0

    def _calculate_quality_score(
        self,
        sharpness: float,
        contrast: float,
        skew: float
    ) -> float:
        """
        Calculate overall quality score (0-1)

        Factors:
        - Sharpness: 40% weight
        - Contrast: 40% weight
        - Skew: 20% weight
        """
        # Normalize sharpness (100-500 range typical for good docs)
        sharpness_score = min(1.0, max(0.0, (sharpness - 50) / 450))

        # Normalize contrast (40-80 range typical for good docs)
        contrast_score = min(1.0, max(0.0, (contrast - 20) / 60))

        # Normalize skew (0-2 degrees acceptable)
        skew_score = max(0.0, 1.0 - (skew / 10.0))

        # Weighted average
        quality_score = (
            sharpness_score * 0.4 +
            contrast_score * 0.4 +
            skew_score * 0.2
        )

        return float(quality_score)

    def _deskew_image(self, img_array: np.ndarray, angle: float) -> np.ndarray:
        """
        Deskew image by rotating by detected angle
        """
        if abs(angle) < 0.1:  # Don't rotate if angle is negligible
            return img_array

        # Get image dimensions
        (h, w) = img_array.shape[:2]
        center = (w // 2, h // 2)

        # Calculate rotation matrix
        M = cv2.getRotationMatrix2D(center, angle, 1.0)

        # Perform rotation
        rotated = cv2.warpAffine(
            img_array, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )

        return rotated

    def _enhance_contrast(self, img_array: np.ndarray) -> np.ndarray:
        """
        Enhance image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
        """
        if len(img_array.shape) == 3:
            # Convert to LAB color space
            lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(lab)

            # Apply CLAHE to L channel
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)

            # Merge channels
            enhanced = cv2.merge([l, a, b])

            # Convert back to RGB
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)
        else:
            # Grayscale image
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(img_array)

        return enhanced

    def _sharpen_image(self, img_array: np.ndarray) -> np.ndarray:
        """
        Sharpen image using unsharp masking
        """
        # Gaussian blur
        blurred = cv2.GaussianBlur(img_array, (0, 0), 3)

        # Unsharp mask
        sharpened = cv2.addWeighted(img_array, 1.5, blurred, -0.5, 0)

        return sharpened

    def _denoise_image(self, img_array: np.ndarray) -> np.ndarray:
        """
        Denoise image using Non-Local Means Denoising
        """
        if len(img_array.shape) == 3:
            denoised = cv2.fastNlMeansDenoisingColored(img_array, None, 10, 10, 7, 21)
        else:
            denoised = cv2.fastNlMeansDenoising(img_array, None, 10, 7, 21)

        return denoised

    def _images_to_pdf(self, images: list) -> bytes:
        """
        Convert list of PIL Images to PDF bytes
        """
        output = io.BytesIO()

        # Save first image as PDF
        images[0].save(
            output,
            format='PDF',
            save_all=True,
            append_images=images[1:] if len(images) > 1 else [],
            resolution=self.dpi
        )

        return output.getvalue()

    def binarize_for_ocr(self, img_array: np.ndarray) -> np.ndarray:
        """
        Binarize image for optimal OCR

        Uses adaptive thresholding
        """
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )

        return binary
