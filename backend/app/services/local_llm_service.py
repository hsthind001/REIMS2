"""
Local LLM Service for Market Intelligence
Supports multiple open-source LLM providers:
- Ollama (primary, local inference)
- Groq (fallback, cloud inference)
- vLLM (optional, high-performance local inference)

Author: REIMS Development Team
Date: 2025-01-09
"""

import json
import logging
from typing import Dict, List, Optional, Union, Any
from enum import Enum
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OLLAMA = "ollama"
    GROQ = "groq"
    VLLM = "vllm"


class LLMModel(str, Enum):
    """Available open-source models"""
    # Fast, lightweight models (2-8GB VRAM)
    LLAMA_3_2_3B = "llama3.2:3b-instruct-q4_K_M"
    QWEN_2_5_7B = "qwen2.5:7b-instruct-q4_K_M"
    
    # Mid-range models (available on system)
    QWEN_2_5_14B = "qwen2.5:14b"
    DEEPSEEK_R1_14B = "deepseek-r1:14b"

    # Balanced models (16-24GB VRAM)
    QWEN_2_5_32B = "qwen2.5:32b-instruct-q4_K_M"
    LLAMA_3_1_70B = "llama3.1:70b-instruct-q4_K_M"

    # Premium models (24-48GB VRAM)
    LLAMA_3_3_70B = "llama3.3:70b-instruct-q4_K_M"
    QWEN_2_5_72B = "qwen2.5:72b-instruct-q4_K_M"

    # Vision models
    LLAVA_13B = "llava:13b-v1.6-vicuna-q4_K_M"
    LLAVA_34B = "llava:34b-v1.6-vicuna-q4_K_M"
    MOONDREAM = "moondream"  # Lightweight vision model (available)

    # Groq cloud models (fallback)
    GROQ_LLAMA_3_3_70B = "llama-3.3-70b-versatile"


class LLMTaskType(str, Enum):
    """Task types for automatic model selection"""
    SUMMARY = "summary"  # Quick summaries, simple tasks
    ANALYSIS = "analysis"  # SWOT, risk assessment
    NARRATIVE = "narrative"  # Investment memos, detailed write-ups
    VISION = "vision"  # Image analysis
    CHAT = "chat"  # Conversational


class LLMConfig(BaseModel):
    """LLM configuration"""
    provider: LLMProvider = LLMProvider.OLLAMA
    model: str = LLMModel.QWEN_2_5_14B  # Default to available system model
    temperature: float = 0.3
    max_tokens: int = 4000
    top_p: float = 0.9
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stream: bool = False

    # Provider-specific endpoints
    ollama_base_url: str = "http://ollama:11434"
    groq_api_key: Optional[str] = None
    vllm_base_url: str = "http://localhost:8001"


class LocalLLMService:
    """
    Service for interacting with local open-source LLMs

    Features:
    - Automatic model selection based on task type
    - Fallback to cloud providers if local unavailable
    - Streaming support for real-time responses
    - Cost tracking and optimization
    - GPU/CPU automatic detection
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self.client = httpx.AsyncClient(
            timeout=300.0,  # 5 min timeout for large models
            headers={"Content-Type": "application/json"}
        )

        # Model selection rules (task_type -> model)
        # Use configured model for all tasks initially (will upgrade when larger models available)
        default_model = self.config.model
        self.model_selector = {
            LLMTaskType.SUMMARY: default_model,  # Fast summaries
            LLMTaskType.ANALYSIS: LLMModel.DEEPSEEK_R1_14B,  # Use Reasoning model for deep analysis
            LLMTaskType.NARRATIVE: default_model,  # Narratives (use larger model when available)
            LLMTaskType.VISION: LLMModel.MOONDREAM,  # Use Moondream (installed) for Vision
            LLMTaskType.CHAT: default_model,  # Chat
        }

    async def _check_ollama_health(self) -> bool:
        """Check if Ollama service is available"""
        try:
            response = await self.client.get(f"{self.config.ollama_base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    async def _list_ollama_models(self) -> List[str]:
        """List available models in Ollama"""
        try:
            response = await self.client.get(f"{self.config.ollama_base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    def select_model(self, task_type: LLMTaskType, prefer_fast: bool = False) -> str:
        """
        Automatically select the best model for the task

        Args:
            task_type: Type of task (summary, analysis, etc.)
            prefer_fast: If True, prefer faster/smaller models

        Returns:
            Model name string
        """
        if prefer_fast:
            # Use lightweight models for speed
            return LLMModel.LLAMA_3_2_3B

        # Fallback to configured default model
        return self.model_selector.get(task_type, self.config.model)

    async def generate(
        self,
        prompt: str,
        task_type: LLMTaskType = LLMTaskType.ANALYSIS,
        system_prompt: Optional[str] = None,
        prefer_fast: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate text using local LLM

        Args:
            prompt: User prompt
            task_type: Type of task for model selection
            system_prompt: Optional system prompt
            prefer_fast: Prefer faster models
            temperature: Override default temperature
            max_tokens: Override default max tokens
            **kwargs: Additional model parameters

        Returns:
            Generated text
        """
        # Select appropriate model
        model = self.select_model(task_type, prefer_fast)

        # Override config if specified
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        logger.info(f"Generating with model: {model}, task: {task_type}")

        # Check if Ollama is available
        if self.config.provider == LLMProvider.OLLAMA:
            ollama_available = await self._check_ollama_health()
            if not ollama_available:
                logger.warning("Ollama unavailable, falling back to Groq")
                return await self._generate_with_groq(prompt, system_prompt, temp, max_tok)

            return await self._generate_with_ollama(
                prompt, model, system_prompt, temp, max_tok, **kwargs
            )

        elif self.config.provider == LLMProvider.GROQ:
            return await self._generate_with_groq(prompt, system_prompt, temp, max_tok)

        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")

    async def _generate_with_ollama(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> str:
        """Generate text using Ollama"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": self.config.top_p,
            }
        }

        try:
            url = f"{self.config.ollama_base_url}/api/chat"
            logger.info(f"Sending request to Ollama: {url}")
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

            response = await self.client.post(url, json=payload)

            logger.info(f"Ollama response status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Ollama error response: {response.text}")

            response.raise_for_status()

            result = response.json()
            logger.info(f"Ollama generation successful, response length: {len(result.get('message', {}).get('content', ''))}")
            return result["message"]["content"]

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Ollama generation failed: {type(e).__name__}: {e}")
            raise

    async def _generate_with_groq(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate text using Groq (fallback)"""
        try:
            from groq import Groq

            if not self.config.groq_api_key:
                raise ValueError("Groq API key not configured")

            client = Groq(api_key=self.config.groq_api_key)

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=LLMModel.GROQ_LLAMA_3_3_70B,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=self.config.top_p,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            raise

    async def generate_json(
        self,
        prompt: str,
        task_type: LLMTaskType = LLMTaskType.ANALYSIS,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict] = None,
        **kwargs
    ) -> Dict:
        """
        Generate structured JSON output

        Args:
            prompt: User prompt (should request JSON output)
            task_type: Type of task
            system_prompt: Optional system prompt
            schema: Optional JSON schema for validation
            **kwargs: Additional parameters

        Returns:
            Parsed JSON dictionary
        """
        # Enhance prompt to request JSON
        json_prompt = f"{prompt}\n\nRespond ONLY with valid JSON. No markdown, no explanations."

        if schema:
            json_prompt += f"\n\nFollow this schema:\n{json.dumps(schema, indent=2)}"

        # Generate response
        response = await self.generate(
            prompt=json_prompt,
            task_type=task_type,
            system_prompt=system_prompt,
            **kwargs
        )

        # Parse JSON (handle markdown code blocks)
        response_clean = response.strip()
        if response_clean.startswith("```json"):
            response_clean = response_clean.replace("```json", "").replace("```", "").strip()
        elif response_clean.startswith("```"):
            response_clean = response_clean.replace("```", "").strip()

        try:
            return json.loads(response_clean)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}\nResponse: {response}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

    async def generate_stream(
        self,
        prompt: str,
        task_type: LLMTaskType = LLMTaskType.ANALYSIS,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """
        Generate text with streaming (for real-time UI updates)

        Args:
            prompt: User prompt
            task_type: Type of task
            system_prompt: Optional system prompt
            **kwargs: Additional parameters

        Yields:
            Text chunks as they are generated
        """
        model = self.select_model(task_type)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            }
        }

        try:
            async with self.client.stream(
                "POST",
                f"{self.config.ollama_base_url}/api/chat",
                json=payload
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line:
                        chunk = json.loads(line)
                        if "message" in chunk and "content" in chunk["message"]:
                            yield chunk["message"]["content"]

        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            raise

    async def analyze_image(
        self,
        image_path: str = None, # Make optional to support direct base64 if needed, but keeping signature
        prompt: str = "Describe this image",
        system_prompt: Optional[str] = None,
        image_b64: Optional[str] = None, # Added to support direct base64 injection
        **kwargs
    ) -> str:
        """
        Analyze an image using vision-language model

        Args:
            image_path: Path to image file (optional if image_b64 provided)
            prompt: Analysis prompt
            system_prompt: Optional system prompt
            image_b64: Optional base64 string (data URI or raw)
            **kwargs: Additional parameters

        Returns:
            Analysis text
        """
        import base64
        
        # Determine model dynamically
        model = self.select_model(LLMTaskType.VISION)

        # Get base64 data
        if image_b64:
            # If it's a data URI (data:image/jpeg;base64,...), strip the prefix
            if "," in image_b64:
                image_data = image_b64.split(",")[1]
            else:
                image_data = image_b64
        elif image_path:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
        else:
            raise ValueError("Must provide either image_path or image_b64")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({
            "role": "user",
            "content": prompt,
            "images": [image_data]
        })

        payload = {
            "model": model, # DYNAMIC MODEL SELECTION
            "messages": messages,
            "stream": False,
        }

        try:
            response = await self.client.post(
                f"{self.config.ollama_base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()

            result = response.json()
            return result["message"]["content"]

        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            raise


    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Singleton instance
_llm_service: Optional[LocalLLMService] = None


def get_local_llm_service() -> LocalLLMService:
    """Get or create LocalLLM service singleton"""
    global _llm_service

    if _llm_service is None:
        from app.core.config import settings

        config = LLMConfig(
            provider=LLMProvider.OLLAMA,
            model=getattr(settings, "OLLAMA_DEFAULT_MODEL", "llama3.2:3b-instruct-q4_K_M"),
            ollama_base_url=getattr(settings, "OLLAMA_BASE_URL", "http://ollama:11434"),
            groq_api_key=getattr(settings, "GROQ_API_KEY", None),
            temperature=getattr(settings, "LLM_TEMPERATURE", 0.3),
            max_tokens=getattr(settings, "LLM_MAX_TOKENS", 4000),
        )

        _llm_service = LocalLLMService(config)

    return _llm_service
