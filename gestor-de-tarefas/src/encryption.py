"""
Encryption utilities using Fernet symmetric encryption.
The encryption key is loaded from environment variables via python-dotenv.
"""
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class EncryptionManager:
    """Manages encryption and decryption of data using Fernet."""
    
    def __init__(self):
        """Initialize the encryption manager with a key from environment variables."""
        self.key = os.getenv("FERNET_KEY")
        
        if not self.key:
            raise ValueError(
                "FERNET_KEY not found in environment variables. "
                "Please set it in your .env file."
            )
        
        # Convert key to bytes if it's a string
        self.key = self.key.encode() if isinstance(self.key, str) else self.key
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt a string.
        
        Args:
            data: The string to encrypt
            
        Returns:
            The encrypted data as a base64-encoded string
        """
        encrypted_bytes = self.cipher.encrypt(data.encode())
        return encrypted_bytes.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt an encrypted string.
        
        Args:
            encrypted_data: The encrypted data as a base64-encoded string
            
        Returns:
            The decrypted string
        """
        decrypted_bytes = self.cipher.decrypt(encrypted_data.encode())
        return decrypted_bytes.decode()


def generate_key() -> str:
    """
    Generate a new Fernet encryption key.
    
    Returns:
        A new Fernet key as a base64-encoded string
    """
    return Fernet.generate_key().decode()


# Example usage for generating a key (run this once to get a key for your .env file)
if __name__ == "__main__":
    print("Generated Fernet key:")
    print(generate_key())
    print("\nAdd this to your .env file as:")
    print("FERNET_KEY=<the_generated_key>")
