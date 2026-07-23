from typing import Dict, Any, Optional
import httpx
import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime

from src.api.models import ClassificationResult, ModelType
from src.config import settings
from src.utils.metrics import MetricsManager

logger = logging.getLogger(__name__)

@dataclass
class RouteResult:
    model: ModelType
    endpoint: str
    metadata: Dict[str, Any]

class RoutingEngine:
    """Intelligent request routing engine"""

    def __init__(self):
        # Model configurations
        self.models = {
            ModelType.OPENAI: {
                "endpoint": settings.OPENAI_ENDPOINT,
                "timeout": 30,
                "api_key": settings.OPENAI_API_KEY,
                "weight": 100
            },
            ModelType.AZURE_OPENAI: {
                #"endpoint": settings.AZURE_OPENAI_ENDPOINT,
                "endpoint": settings.OPENAI_ENDPOINT,
                "timeout": 30,
                #"api_key": settings.AZURE_OPENAI_API_KEY,
                "api_key": settings.OPENAI_API_KEY,
                "weight": 80
            },
            ModelType.ANTHROPIC: {
                "endpoint": settings.ANTHROPIC_ENDPOINT,
                "timeout": 30,
                "api_key": settings.ANTHROPIC_API_KEY,
                "weight": 70
            },
            ModelType.LOCAL_LLAMA: {
                "endpoint": settings.LOCAL_LLAMA_ENDPOINT,
                "timeout": 60,
                "api_key": None,
                "weight": 30
            }
        }

        # Health status
        self.health_status = {model: True for model in ModelType}
        self.last_health_check = {}

        # Initialize HTTP client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=100, max_connections=200)
        )

        # Response cache
        self.cache = {}

    async def route(
        self,
        prompt: str,
        classification: ClassificationResult,
        preference: Optional[ModelType] = None
    ) -> ModelType:
        """Determine which model to route to"""

        # If preference provided and healthy, use it
        if preference and self.health_status.get(preference, False):
            return preference

        # Determine based on risk and classification
        if classification.risk_level == "critical":
            return ModelType.LOCAL_LLAMA
        elif classification.risk_level == "high":
            return ModelType.AZURE_OPENAI
        elif classification.risk_level == "medium":
            # Weighted selection between Azure and Anthropic
            available = [ModelType.AZURE_OPENAI, ModelType.ANTHROPIC]
            weights = [80, 20]
            return random.choices(available, weights=weights)[0]
        else:  # low risk
            # Weighted selection
            available = [ModelType.OPENAI, ModelType.AZURE_OPENAI, ModelType.ANTHROPIC]
            weights = [50, 30, 20]
            return random.choices(available, weights=weights)[0]

    async def send_to_model(
        self,
        model: ModelType,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send request to selected model"""

        model_config = self.models.get(model)
        if not model_config:
            raise ValueError(f"Model {model} not configured")

        # Check cache
        cache_key = f"{model}_{prompt[:100]}_{hash(str(context))}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Prepare request
        endpoint = model_config["endpoint"]
        api_key = model_config.get("api_key")
        timeout = model_config.get("timeout", 30)

        # Build payload based on model type
        if model == ModelType.OPENAI:
            payload = {
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

        elif model == ModelType.AZURE_OPENAI:
            payload = {
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            headers = {
                "api-key": api_key,
                "Content-Type": "application/json"
            }

        elif model == ModelType.ANTHROPIC:
            payload = {
                "model": "claude-3-opus-20240229",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.7
            }
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }

        elif model == ModelType.LOCAL_LLAMA:
            payload = {
                "model": "llama2",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7}
            }
            headers = {"Content-Type": "application/json"}

        else:
            raise ValueError(f"Unsupported model: {model}")

        # Update metrics
        MetricsManager.record_model_request(model)

        try:
            # Send request
            response = await self.client.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()

            # Parse response
            response_data = response.json()
            text = self._extract_text(response_data, model)

            # Cache response
            if len(self.cache) > 1000:
                # Remove oldest
                self.cache.pop(next(iter(self.cache)))
            self.cache[cache_key] = text

            return text

        except httpx.TimeoutException:
            logger.error(f"Timeout sending to {model}")
            MetricsManager.record_model_error(model, "timeout")

            # Try fallback if available
            if model != ModelType.LOCAL_LLAMA:
                logger.info(f"Falling back to local model")
                return await self.send_to_model(
                    ModelType.LOCAL_LLAMA,
                    prompt,
                    context
                )
            raise

        except Exception as e:
            logger.error(f"Error sending to {model}: {str(e)}")
            MetricsManager.record_model_error(model, str(e))
            raise

    def _extract_text(self, response_data: Dict[str, Any], model: ModelType) -> str:
        """Extract text from model response"""
        try:
            if model == ModelType.OPENAI:
                return response_data["choices"][0]["message"]["content"]
            elif model == ModelType.AZURE_OPENAI:
                return response_data["choices"][0]["message"]["content"]
            elif model == ModelType.ANTHROPIC:
                return response_data["content"][0]["text"]
            elif model == ModelType.LOCAL_LLAMA:
                return response_data.get("response", "")
            else:
                return str(response_data)
        except (KeyError, IndexError):
            logger.error(f"Failed to extract text from {model} response")
            return str(response_data)

    async def health_check(self, model: ModelType) -> bool:
        """Check if a model is healthy"""
        if model not in self.models:
            return False

        # Check if recently checked
        last_check = self.last_health_check.get(model)
        if last_check and (datetime.utcnow() - last_check).seconds < 60:
            return self.health_status.get(model, False)

        model_config = self.models[model]
        endpoint = model_config["endpoint"]

        try:
            # Simple health check
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    endpoint.replace("/chat/completions", "/health"),
                    timeout=2.0
                )
                status = response.status_code == 200
                self.health_status[model] = status
                self.last_health_check[model] = datetime.utcnow()
                return status
        except:
            self.health_status[model] = False
            self.last_health_check[model] = datetime.utcnow()
            return False

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
