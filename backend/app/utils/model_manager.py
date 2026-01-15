import logging

logger = logging.getLogger(__name__)

class ModelManager:
    """
    Singleton manager for heavy ML models and engines.
    Ensures models are loaded only once per worker process.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._ocr_engine = None
        self._layoutlm_engine = None
        self._easyocr_engine = None
        self._camelot_engine = None
        self._initialized = True
        
        logger.info("ModelManager initialized")

    @property
    def ocr_engine(self):
        if self._ocr_engine is None:
            try:
                logger.info("Loading OCR Engine...")
                from app.utils.engines.ocr_engine import OCREngine
                self._ocr_engine = OCREngine()
            except ImportError as e:
                logger.warning(f"Failed to load OCR Engine: {e}")
                self._ocr_engine = False # Marker for failed load
            except Exception as e:
                logger.error(f"Error initializing OCR Engine: {e}")
                self._ocr_engine = False

        return self._ocr_engine if self._ocr_engine is not False else None

    @property
    def layoutlm_engine(self):
        if self._layoutlm_engine is None:
            try:
                logger.info("Loading LayoutLM Engine...")
                from app.utils.engines.layoutlm_engine import LayoutLMEngine
                self._layoutlm_engine = LayoutLMEngine()
            except ImportError as e:
                logger.warning(f"Failed to load LayoutLM Engine: {e}")
                self._layoutlm_engine = False
            except Exception as e:
                logger.error(f"Error initializing LayoutLM Engine: {e}")
                self._layoutlm_engine = False
                
        return self._layoutlm_engine if self._layoutlm_engine is not False else None

    @property
    def easyocr_engine(self):
        if self._easyocr_engine is None:
            try:
                logger.info("Loading EasyOCR Engine...")
                from app.utils.engines.easyocr_engine import EasyOCREngine
                self._easyocr_engine = EasyOCREngine()
            except ImportError as e:
                logger.warning(f"Failed to load EasyOCR Engine: {e}")
                self._easyocr_engine = False
            except Exception as e:
                logger.error(f"Error initializing EasyOCR Engine: {e}")
                self._easyocr_engine = False
                
        return self._easyocr_engine if self._easyocr_engine is not False else None

    @property
    def camelot_engine(self):
        if self._camelot_engine is None:
            try:
                logger.info("Loading Camelot Engine...")
                from app.utils.engines.camelot_engine import CamelotEngine
                self._camelot_engine = CamelotEngine()
            except ImportError as e:
                logger.warning(f"Failed to load Camelot Engine: {e}")
                self._camelot_engine = False
            except Exception as e:
                logger.error(f"Error initializing Camelot Engine: {e}")
                self._camelot_engine = False
                
        return self._camelot_engine if self._camelot_engine is not False else None

# Global instance
model_manager = ModelManager()
