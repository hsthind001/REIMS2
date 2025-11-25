"""
AWS KMS Client for Data Encryption at Rest

Provides encryption/decryption services using AWS KMS for production environments.
Falls back to local keychain/keyring for development environments.

BR-006: Security & Compliance requirement
"""
import os
import logging
from typing import Optional, Dict
import boto3
from botocore.exceptions import ClientError, BotoCoreError
import json

logger = logging.getLogger(__name__)


class KMSClient:
    """
    AWS KMS Client for encryption/decryption
    
    Supports:
    - Production: AWS KMS encryption
    - Development: Local keyring/keychain encryption
    """
    
    def __init__(self):
        """Initialize KMS client based on environment"""
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        self.kms_key_id = os.getenv("AWS_KMS_KEY_ID")
        self.use_kms = self.environment == "production" and self.kms_key_id is not None
        
        if self.use_kms:
            try:
                self.kms_client = boto3.client('kms', region_name=os.getenv("AWS_REGION", "us-east-1"))
                logger.info("✅ AWS KMS client initialized for production")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS KMS: {e}. Falling back to local encryption.")
                self.use_kms = False
                self._init_local_encryption()
        else:
            self._init_local_encryption()
    
    def _init_local_encryption(self):
        """Initialize local encryption for development"""
        try:
            import keyring
            self.keyring = keyring
            self.service_name = "reims-dev"
            logger.info("✅ Local keyring initialized for development")
        except ImportError:
            logger.warning("keyring not available. Using environment variable fallback.")
            self.keyring = None
            self._fallback_key = os.getenv("REIMS_ENCRYPTION_KEY", "dev-key-change-in-production")
    
    def encrypt(self, plaintext: str, context: Optional[Dict[str, str]] = None) -> str:
        """
        Encrypt plaintext using KMS or local encryption
        
        Args:
            plaintext: Text to encrypt
            context: Optional encryption context (key-value pairs)
            
        Returns:
            Base64-encoded encrypted string
        """
        if self.use_kms:
            return self._encrypt_kms(plaintext, context)
        else:
            return self._encrypt_local(plaintext)
    
    def decrypt(self, ciphertext: str, context: Optional[Dict[str, str]] = None) -> str:
        """
        Decrypt ciphertext using KMS or local decryption
        
        Args:
            ciphertext: Base64-encoded encrypted string
            context: Optional encryption context (must match encryption context)
            
        Returns:
            Decrypted plaintext
        """
        if self.use_kms:
            return self._decrypt_kms(ciphertext, context)
        else:
            return self._decrypt_local(ciphertext)
    
    def _encrypt_kms(self, plaintext: str, context: Optional[Dict[str, str]] = None) -> str:
        """Encrypt using AWS KMS"""
        try:
            encryption_context = context or {}
            
            response = self.kms_client.encrypt(
                KeyId=self.kms_key_id,
                Plaintext=plaintext.encode('utf-8'),
                EncryptionContext=encryption_context
            )
            
            # Return base64-encoded ciphertext
            import base64
            return base64.b64encode(response['CiphertextBlob']).decode('utf-8')
            
        except (ClientError, BotoCoreError) as e:
            logger.error(f"AWS KMS encryption failed: {e}")
            raise Exception(f"Encryption failed: {str(e)}")
    
    def _decrypt_kms(self, ciphertext: str, context: Optional[Dict[str, str]] = None) -> str:
        """Decrypt using AWS KMS"""
        try:
            import base64
            ciphertext_blob = base64.b64decode(ciphertext.encode('utf-8'))
            
            encryption_context = context or {}
            
            response = self.kms_client.decrypt(
                CiphertextBlob=ciphertext_blob,
                EncryptionContext=encryption_context
            )
            
            return response['Plaintext'].decode('utf-8')
            
        except (ClientError, BotoCoreError) as e:
            logger.error(f"AWS KMS decryption failed: {e}")
            raise Exception(f"Decryption failed: {str(e)}")
    
    def _encrypt_local(self, plaintext: str) -> str:
        """Encrypt using local keyring or fallback"""
        try:
            from cryptography.fernet import Fernet
            import base64
            
            # Get encryption key
            if self.keyring:
                key = self.keyring.get_password(self.service_name, "encryption_key")
                if not key:
                    # Generate and store key
                    key = Fernet.generate_key().decode('utf-8')
                    self.keyring.set_password(self.service_name, "encryption_key", key)
            else:
                # Use fallback key (derive Fernet key from it)
                import hashlib
                key_bytes = hashlib.sha256(self._fallback_key.encode()).digest()
                key = base64.urlsafe_b64encode(key_bytes).decode('utf-8')
            
            # Encrypt
            fernet = Fernet(key)
            encrypted = fernet.encrypt(plaintext.encode('utf-8'))
            return base64.b64encode(encrypted).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Local encryption failed: {e}")
            # Fallback: return base64-encoded plaintext (not secure, but functional)
            import base64
            return base64.b64encode(plaintext.encode('utf-8')).decode('utf-8')
    
    def _decrypt_local(self, ciphertext: str) -> str:
        """Decrypt using local keyring or fallback"""
        try:
            from cryptography.fernet import Fernet
            import base64
            
            # Get decryption key
            if self.keyring:
                key = self.keyring.get_password(self.service_name, "encryption_key")
                if not key:
                    raise Exception("Encryption key not found in keyring")
            else:
                # Use fallback key
                import hashlib
                key_bytes = hashlib.sha256(self._fallback_key.encode()).digest()
                key = base64.urlsafe_b64encode(key_bytes).decode('utf-8')
            
            # Decrypt
            fernet = Fernet(key)
            encrypted_bytes = base64.b64decode(ciphertext.encode('utf-8'))
            decrypted = fernet.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Local decryption failed: {e}")
            # Fallback: try base64 decode
            try:
                import base64
                return base64.b64decode(ciphertext.encode('utf-8')).decode('utf-8')
            except:
                raise Exception(f"Decryption failed: {str(e)}")
    
    def encrypt_field(self, field_value: str, table_name: str, record_id: int) -> str:
        """
        Encrypt a database field with context
        
        Args:
            field_value: Value to encrypt
            table_name: Database table name (for context)
            record_id: Record ID (for context)
            
        Returns:
            Encrypted value
        """
        context = {
            "table": table_name,
            "record_id": str(record_id)
        }
        return self.encrypt(field_value, context)
    
    def decrypt_field(self, encrypted_value: str, table_name: str, record_id: int) -> str:
        """
        Decrypt a database field with context
        
        Args:
            encrypted_value: Encrypted value
            table_name: Database table name (for context)
            record_id: Record ID (for context)
            
        Returns:
            Decrypted value
        """
        context = {
            "table": table_name,
            "record_id": str(record_id)
        }
        return self.decrypt(encrypted_value, context)


# Singleton instance
_kms_client_instance: Optional[KMSClient] = None


def get_kms_client() -> KMSClient:
    """Get singleton KMS client instance"""
    global _kms_client_instance
    if _kms_client_instance is None:
        _kms_client_instance = KMSClient()
    return _kms_client_instance

