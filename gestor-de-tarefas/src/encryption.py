import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class EncryptionManager:    
    def __init__(self):
        self.key = os.getenv("FERNET_KEY")
        
        if not self.key:
            raise ValueError(
                "FERNET_KEY not found in environment variables. "
                "Please set it in your .env file."
            )
        
        self.key = self.key.encode() if isinstance(self.key, str) else self.key
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        encrypted_bytes = self.cipher.encrypt(data.encode())
        return encrypted_bytes.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        decrypted_bytes = self.cipher.decrypt(encrypted_data.encode())
        return decrypted_bytes.decode()

# Apenas usar se pretender gerar uma nova chave.
#def generate_key() -> str:
    #return Fernet.generate_key().decode()

#if __name__ == "__main__":
    #print("Generated Fernet key:")
    #print(generate_key())
    #print("\nAdd this to your .env file as:")
    #print("FERNET_KEY=<the_generated_key>")
