
import json
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

CORRECTIONS_FILE = os.path.join(os.path.dirname(__file__), "../../data/corrections_db.json")

class FeedbackLoopService:
    """
    Service to manage the Active Learning feedback loop.
    Stores user corrections to extraction results and retrieves them
    as Few-Shot examples for future LLM prompts.
    """

    def __init__(self, data_path: str = CORRECTIONS_FILE):
        self.data_path = data_path
        self._ensure_storage()

    def _ensure_storage(self):
        """Ensure the JSON storage file exists."""
        dirname = os.path.dirname(self.data_path)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)
            
        if not os.path.exists(self.data_path):
            with open(self.data_path, 'w') as f:
                json.dump({"balance_sheet": [], "income_statement": [], "rent_roll": []}, f)

    def _load_data(self) -> Dict:
        try:
            with open(self.data_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_data(self, data: Dict):
        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def save_correction(
        self, 
        original_text: str, 
        user_corrected_json: Dict, 
        document_type: str,
        notes: str = ""
    ) -> bool:
        """
        Save a user-verified correction as a training example.
        """
        try:
            data = self._load_data()
            if document_type not in data:
                data[document_type] = []
            
            # Create example record
            example = {
                "id": len(data[document_type]) + 1,
                "timestamp": datetime.now().isoformat(),
                "text_snippet": original_text[:1000], # Store first 1k chars as context
                "expected_json": user_corrected_json,
                "notes": notes
            }
            
            data[document_type].append(example)
            self._save_data(data)
            logger.info(f"Saved correction for {document_type} (Total: {len(data[document_type])})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save correction: {e}")
            return False

    def get_few_shot_examples(self, document_type: str, limit: int = 3) -> List[Dict]:
        """
        Retrieve relevant examples for the prompt.
        Currently returns the most recent examples.
        Future: Use vector similarity search.
        """
        data = self._load_data()
        examples = data.get(document_type, [])
        
        # Return recent ones (mocking relevance)
        return examples[-limit:]
