#!/usr/bin/env python
"""Initialize secrets in Vault"""

import os
import hvac
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_vault():
    """Initialize Vault with model secrets"""
    vault_url = os.getenv('VAULT_URL', 'http://localhost:8200')
    vault_token = os.getenv('VAULT_TOKEN', 'root')
    
    client = hvac.Client(
        url=vault_url,
        token=vault_token
    )
    
    if not client.is_authenticated():
        logger.error("Vault authentication failed")
        return False
    
    # Model secrets
    secrets = {
        'openai-key': os.getenv('OPENAI_API_KEY', ''),
        'azure-key': os.getenv('AZURE_OPENAI_API_KEY', ''),
        'anthropic-key': os.getenv('ANTHROPIC_API_KEY', ''),
        'jwt-secret': os.getenv('JWT_SECRET', 'change-me'),
        'encryption-key': os.getenv('ENCRYPTION_KEY', 'change-me')
    }
    
    # Store secrets
    for key, value in secrets.items():
        if value:
            client.secrets.kv.v2.create_or_update_secret(
                path=f"ai-control-plane/{key}",
                secret={"value": value},
                mount_point="secret"
            )
            logger.info(f"Stored secret: {key}")
        else:
            logger.warning(f"Secret {key} not provided")
    
    logger.info("✅ Secrets initialized")
    return True

if __name__ == "__main__":
    init_vault()