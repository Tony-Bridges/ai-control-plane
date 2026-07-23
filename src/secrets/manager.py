from typing import Optional, Dict, Any
import logging
import json
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class SecretsManager(ABC):
    """Base secrets manager"""
    
    @abstractmethod
    async def get_secret(self, key: str) -> Optional[str]:
        """Get secret by key"""
        pass
    
    @abstractmethod
    async def set_secret(self, key: str, value: str):
        """Set secret"""
        pass
    
    @abstractmethod
    async def delete_secret(self, key: str):
        """Delete secret"""
        pass

class HashicorpVaultManager(SecretsManager):
    """Hashicorp Vault implementation"""
    
    def __init__(self, vault_url: str, token: str):
        self.vault_url = vault_url.rstrip('/')
        self.token = token
        self.client = None
        
    async def initialize(self):
        """Initialize Vault client"""
        import hvac
        self.client = hvac.Client(
            url=self.vault_url,
            token=self.token
        )
        
        if not self.client.is_authenticated():
            raise Exception("Vault authentication failed")
        
        logger.info("Vault client initialized")
    
    async def get_secret(self, key: str) -> Optional[str]:
        """Get secret from Vault"""
        try:
            secret_path = f"secret/data/{key}"
            response = self.client.secrets.kv.v2.read_secret_version(
                path=key,
                mount_point="secret"
            )
            return response["data"]["data"].get("value")
        except Exception as e:
            logger.error(f"Failed to get secret {key}: {str(e)}")
            return None
    
    async def set_secret(self, key: str, value: str):
        """Set secret in Vault"""
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=key,
                secret={"value": value},
                mount_point="secret"
            )
        except Exception as e:
            logger.error(f"Failed to set secret {key}: {str(e)}")
            raise
    
    async def delete_secret(self, key: str):
        """Delete secret from Vault"""
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=key,
                mount_point="secret"
            )
        except Exception as e:
            logger.error(f"Failed to delete secret {key}: {str(e)}")
            raise

class AzureKeyVaultManager(SecretsManager):
    """Azure Key Vault implementation"""
    
    def __init__(self, vault_url: str, credential):
        self.vault_url = vault_url.rstrip('/')
        self.credential = credential
        self.client = None
        
    async def initialize(self):
        """Initialize Azure Key Vault client"""
        from azure.keyvault.secrets import SecretClient
        self.client = SecretClient(
            vault_url=self.vault_url,
            credential=self.credential
        )
        logger.info("Azure Key Vault client initialized")
    
    async def get_secret(self, key: str) -> Optional[str]:
        """Get secret from Azure Key Vault"""
        try:
            secret = self.client.get_secret(key)
            return secret.value
        except Exception as e:
            logger.error(f"Failed to get secret {key}: {str(e)}")
            return None
    
    async def set_secret(self, key: str, value: str):
        """Set secret in Azure Key Vault"""
        try:
            self.client.set_secret(key, value)
        except Exception as e:
            logger.error(f"Failed to set secret {key}: {str(e)}")
            raise
    
    async def delete_secret(self, key: str):
        """Delete secret from Azure Key Vault"""
        try:
            self.client.begin_delete_secret(key)
        except Exception as e:
            logger.error(f"Failed to delete secret {key}: {str(e)}")
            raise

class AWSSecretsManager(SecretsManager):
    """AWS Secrets Manager implementation"""
    
    def __init__(self, region: str):
        self.region = region
        self.client = None
        
    async def initialize(self):
        """Initialize AWS Secrets Manager client"""
        import boto3
        self.client = boto3.client(
            'secretsmanager',
            region_name=self.region
        )
        logger.info("AWS Secrets Manager client initialized")
    
    async def get_secret(self, key: str) -> Optional[str]:
        """Get secret from AWS Secrets Manager"""
        try:
            response = self.client.get_secret_value(SecretId=key)
            return response['SecretString']
        except Exception as e:
            logger.error(f"Failed to get secret {key}: {str(e)}")
            return None
    
    async def set_secret(self, key: str, value: str):
        """Set secret in AWS Secrets Manager"""
        try:
            self.client.create_secret(
                Name=key,
                SecretString=value
            )
        except self.client.exceptions.ResourceExistsException:
            self.client.update_secret(
                SecretId=key,
                SecretString=value
            )
        except Exception as e:
            logger.error(f"Failed to set secret {key}: {str(e)}")
            raise
    
    async def delete_secret(self, key: str):
        """Delete secret from AWS Secrets Manager"""
        try:
            self.client.delete_secret(
                SecretId=key,
                ForceDeleteWithoutRecovery=True
            )
        except Exception as e:
            logger.error(f"Failed to delete secret {key}: {str(e)}")
            raise

class SecretsManagerFactory:
    """Factory for secrets managers"""
    
    @staticmethod
    async def create(provider: str, config: Dict[str, Any]) -> SecretsManager:
        """Create secrets manager instance"""
        if provider == "hashicorp_vault":
            manager = HashicorpVaultManager(
                vault_url=config["vault_url"],
                token=config["token"]
            )
        elif provider == "azure_keyvault":
            from azure.identity import DefaultAzureCredential
            credential = DefaultAzureCredential()
            manager = AzureKeyVaultManager(
                vault_url=config["vault_url"],
                credential=credential
            )
        elif provider == "aws_secrets":
            manager = AWSSecretsManager(
                region=config["region"]
            )
        else:
            raise ValueError(f"Unsupported secrets provider: {provider}")
        
        await manager.initialize()
        return manager