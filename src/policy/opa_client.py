import httpx
import json
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin

from src.config import settings

logger = logging.getLogger(__name__)

class OpaClient:
    """Client for Open Policy Agent"""

    def __init__(self):
        self.base_url = settings.OPA_URL.rstrip('/')
        self.policy_package = "ai_control"
        self.timeout = httpx.Timeout(5.0, read=10.0)
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def evaluate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate input against policies"""

        url = urljoin(self.base_url, f"/v1/data/{self.policy_package}")

        try:
            response = await self.client.post(
                url,
                json={"input": input_data}
            )
            response.raise_for_status()

            result = response.json()

            # Extract decision
            if result.get("result"):
                return result["result"]
            else:
                logger.warning("No policy decision found, using default block")
                return {"action": "block", "reason": "No policy matched"}

        except httpx.TimeoutException:
            logger.error("OPA request timed out")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"OPA returned error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"OPA evaluation failed: {str(e)}")
            raise

    async def create_policy(self, policy_data: Dict[str, Any]) -> bool:
        """Create a new policy in OPA"""

        policy_id = policy_data.get("id")
        if not policy_id:
            raise ValueError("Policy ID required")

        # Build policy document
        policy_doc = {
            "apiVersion": "v1",
            "kind": "Policy",
            "metadata": {
                "name": policy_id,
                "description": policy_data.get("description", "")
            },
            "spec": policy_data.get("spec", {})
        }

        url = urljoin(self.base_url, f"/v1/policies/{policy_id}")

        try:
            response = await self.client.put(
                url,
                json=policy_doc,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to create policy: {str(e)}")
            return False

    async def update_policy(self, policy_id: str, policy_data: Dict[str, Any]) -> bool:
        """Update existing policy"""
        return await self.create_policy(policy_data)  # PUT updates existing

    async def delete_policy(self, policy_id: str) -> bool:
        """Delete policy"""
        url = urljoin(self.base_url, f"/v1/policies/{policy_id}")

        try:
            response = await self.client.delete(url)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to delete policy: {str(e)}")
            return False

    async def list_policies(self) -> List[Dict[str, Any]]:
        """List all policies"""
        url = urljoin(self.base_url, "/v1/policies")

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json().get("result", [])
        except Exception as e:
            logger.error(f"Failed to list policies: {str(e)}")
            return []

    @staticmethod
    async def health_check() -> bool:
        """Check if OPA is healthy"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    urljoin(settings.OPA_URL, "/health"),
                    timeout=2.0
                )
                return response.status_code == 200
        except:
            return False

    async def close(self):
        """Close client session"""
        await self.client.aclose()
