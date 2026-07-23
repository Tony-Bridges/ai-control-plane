from typing import Dict, Any, Optional, List, Tuple
import httpx
import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio

from src.api.models import ClassificationResult, ModelType, RiskLevel
from src.config import settings
from src.utils.metrics import MetricsManager
from src.utils.cache import CacheManager

logger = logging.getLogger(__name__)

@dataclass
class ModelEndpoint:
    model: ModelType
    endpoint: str
    cost_per_1k: float
    latency_avg_ms: float
    availability: float
    regions: List[str]
    weight: int
    is_active: bool = True

class EnhancedRouter:
    """Advanced routing engine with cost, latency, and region awareness"""
    
    def __init__(self):
        self.models = self._init_models()
        self.health_status = {}
        self.latency_history = {}
        self.cost_cache = CacheManager()
        
        # Initialize HTTP client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=200, max_connections=400)
        )
        
        # Health check scheduler
        self._start_health_checker()
    
    def _init_models(self) -> Dict[ModelType, ModelEndpoint]:
        """Initialize model endpoints with metadata"""
        return {
            ModelType.OPENAI: ModelEndpoint(
                model=ModelType.OPENAI,
                endpoint=settings.OPENAI_ENDPOINT,
                cost_per_1k=0.03,
                latency_avg_ms=800,
                availability=0.999,
                regions=["US", "EU"],
                weight=50
            ),
            ModelType.AZURE_OPENAI: ModelEndpoint(
                model=ModelType.AZURE_OPENAI,
                endpoint=settings.AZURE_OPENAI_ENDPOINT,
                cost_per_1k=0.025,
                latency_avg_ms=400,
                availability=0.999,
                regions=["US", "EU", "ZA"],
                weight=80
            ),
            ModelType.ANTHROPIC: ModelEndpoint(
                model=ModelType.ANTHROPIC,
                endpoint=settings.ANTHROPIC_ENDPOINT,
                cost_per_1k=0.035,
                latency_avg_ms=600,
                availability=0.995,
                regions=["US", "EU"],
                weight=20
            ),
            ModelType.LOCAL_LLAMA: ModelEndpoint(
                model=ModelType.LOCAL_LLAMA,
                endpoint=settings.LOCAL_LLAMA_ENDPOINT,
                cost_per_1k=0.005,
                latency_avg_ms=1500,
                availability=0.99,
                regions=["ZA", "US"],
                weight=30
            )
        }
    
    async def route(
        self,
        classification: ClassificationResult,
        context: Dict[str, Any]
    ) -> ModelType:
        """Intelligent routing based on multiple factors"""
        
        tenant_id = context.get("tenant_id")
        region = context.get("region", "global")
        max_cost = context.get("cost_constraint")
        max_latency = context.get("max_latency_ms")
        
        # Get available models
        available_models = await self._get_available_models(
            classification,
            tenant_id,
            region
        )
        
        if not available_models:
            # Fallback to local model
            return ModelType.LOCAL_LLAMA
        
        # Score each model
        scored_models = []
        for model in available_models:
            score = await self._score_model(
                model,
                classification,
                max_cost,
                max_latency,
                region
            )
            scored_models.append((model, score))
        
        # Sort by score descending
        scored_models.sort(key=lambda x: x[1], reverse=True)
        
        # Weighted random selection from top 3
        top_models = scored_models[:3]
        weights = [score for _, score in top_models]
        selected_model = random.choices(
            [model for model, _ in top_models],
            weights=weights,
            k=1
        )[0]
        
        # Update metrics
        MetricsManager.record_routing_decision(
            selected_model,
            classification.risk_level,
            context
        )
        
        return selected_model
    
    async def _get_available_models(
        self,
        classification: ClassificationResult,
        tenant_id: Optional[str],
        region: str
    ) -> List[ModelEndpoint]:
        """Get models available based on tenant and region"""
        
        available = []
        
        for model, endpoint in self.models.items():
            # Check if model is allowed for tenant
            if tenant_id:
                allowed = await self._check_tenant_model_allowed(
                    tenant_id,
                    model
                )
                if not allowed:
                    continue
            
            # Check region
            if region != "global" and region not in endpoint.regions:
                continue
            
            # Check if available for classification
            if not self._is_model_available_for_classification(
                model,
                classification
            ):
                continue
            
            # Check health
            if not await self._is_model_healthy(model):
                continue
            
            available.append(endpoint)
        
        return available
    
    async def _score_model(
        self,
        model: ModelEndpoint,
        classification: ClassificationResult,
        max_cost: Optional[float],
        max_latency: Optional[int],
        region: str
    ) -> float:
        """Score model based on multiple factors"""
        
        score = 100.0  # Base score
        
        # Cost factor
        if max_cost:
            if model.cost_per_1k > max_cost:
                score -= 50  # Penalty for exceeding budget
            else:
                # Higher score for lower cost
                cost_score = (max_cost - model.cost_per_1k) / max_cost * 20
                score += cost_score
        
        # Latency factor
        if max_latency:
            if model.latency_avg_ms > max_latency:
                score -= 30  # Penalty for exceeding latency
            else:
                # Higher score for lower latency
                latency_score = (max_latency - model.latency_avg_ms) / max_latency * 20
                score += latency_score
        
        # Region factor
        if region != "global":
            if region in model.regions:
                score += 15  # Bonus for local models
            else:
                score -= 10  # Penalty for non-local models
        
        # Risk factor
        if classification.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            if model.model == ModelType.LOCAL_LLAMA:
                score += 30  # Bonus for local models on high risk
            elif model.model in [ModelType.OPENAI, ModelType.ANTHROPIC]:
                score -= 20  # Penalty for cloud models on high risk
        
        # Availability factor
        score += model.availability * 10
        
        # Weight factor
        score += model.weight / 10
        
        return max(0, score)
    
    def _is_model_available_for_classification(
        self,
        model: ModelType,
        classification: ClassificationResult
    ) -> bool:
        """Check if model is available for classification"""
        
        # Medical data restrictions
        if classification.classification == "medical":
            if model in [ModelType.OPENAI, ModelType.ANTHROPIC]:
                return False
        
        # Financial data restrictions
        if classification.classification == "financial":
            if model == ModelType.OPENAI:
                return False
        
        # High risk - only local models
        if classification.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            if model != ModelType.LOCAL_LLAMA:
                return False
        
        return True
    
    async def _check_tenant_model_allowed(
        self,
        tenant_id: str,
        model: ModelType
    ) -> bool:
        """Check if tenant is allowed to use model"""
        # Get tenant configuration
        from src.tenant.manager import TenantManager
        tenant_manager = TenantManager()
        tenant = await tenant_manager.get_tenant(tenant_id)
        
        if not tenant:
            return False
        
        tenant_config = tenant.get("config", {})
        allowed_models = tenant_config.get("allowed_models", [])
        
        if not allowed_models:
            return True
        
        return model.value in allowed_models
    
    async def _is_model_healthy(self, model: ModelType) -> bool:
        """Check if model is healthy"""
        # Check cache
        cache_key = f"model_health:{model.value}"
        cached = await self.cost_cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Check health
        try:
            endpoint = self.models[model].endpoint
            health_endpoint = endpoint.replace("/chat/completions", "/health")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    health_endpoint,
                    timeout=2.0
                )
                is_healthy = response.status_code == 200
                
                # Cache for 30 seconds
                await self.cost_cache.set(cache_key, is_healthy, ttl=30)
                
                return is_healthy
        except:
            return False
    
    def _start_health_checker(self):
        """Start periodic health checks"""
        async def health_loop():
            while True:
                for model in self.models:
                    await self._is_model_healthy(model)
                await asyncio.sleep(30)
        
        asyncio.create_task(health_loop())
    
    async def send_to_model(
        self,
        model: ModelType,
        prompt: str,
        context: Dict[str, Any]
    ) -> str:
        """Send request to selected model"""
        
        endpoint = self.models[model]
        
        # Prepare request
        payload = self._prepare_payload(model, prompt, context)
        headers = self._prepare_headers(model, context)
        
        try:
            response = await self.client.post(
                endpoint.endpoint,
                json=payload,
                headers=headers,
                timeout=endpoint.latency_avg_ms / 1000 + 5
            )
            response.raise_for_status()
            
            # Extract text
            text = self._extract_text(response.json(), model)
            
            # Update latency metrics
            latency = response.elapsed.total_seconds() * 1000
            MetricsManager.record_model_latency(model, latency)
            
            return text
            
        except Exception as e:
            logger.error(f"Error sending to {model}: {str(e)}")
            MetricsManager.record_model_error(model, str(e))
            
            # Try fallback if available
            if model != ModelType.LOCAL_LLAMA:
                logger.info(f"Falling back to {ModelType.LOCAL_LLAMA}")
                return await self.send_to_model(
                    ModelType.LOCAL_LLAMA,
                    prompt,
                    context
                )
            raise
    
    def _prepare_payload(
        self,
        model: ModelType,
        prompt: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare payload for model"""
        if model == ModelType.OPENAI:
            return {
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": context.get("system_prompt", "You are a helpful assistant.")},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": context.get("max_tokens", 2000)
            }
        elif model == ModelType.AZURE_OPENAI:
            return {
                "messages": [
                    {"role": "system", "content": context.get("system_prompt", "You are a helpful assistant.")},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": context.get("max_tokens", 2000)
            }
        elif model == ModelType.ANTHROPIC:
            return {
                "model": "claude-3-opus-20240229",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": context.get("max_tokens", 2000),
                "temperature": 0.7
            }
        elif model == ModelType.LOCAL_LLAMA:
            return {
                "model": "llama2",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": context.get("max_tokens", 2000)
                }
            }
        else:
            raise ValueError(f"Unsupported model: {model}")
    
    def _prepare_headers(
        self,
        model: ModelType,
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Prepare headers for model"""
        if model == ModelType.OPENAI:
            return {
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
        elif model == ModelType.AZURE_OPENAI:
            return {
                "api-key": settings.AZURE_OPENAI_API_KEY,
                "Content-Type": "application/json"
            }
        elif model == ModelType.ANTHROPIC:
            return {
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
        elif model == ModelType.LOCAL_LLAMA:
            return {
                "Content-Type": "application/json"
            }
        else:
            return {}
    
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
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to extract text from {model} response: {str(e)}")
            return str(response_data)