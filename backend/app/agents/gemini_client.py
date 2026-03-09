"""
Mistral AI Client
Replaces Gemini with Mistral Large Latest
"""
import os
from mistralai.client import MistralClient


class GeminiClient:
    """Mistral LLM Client (keeping GeminiClient name for compatibility)"""
    
    def __init__(self, api_key=None):
        api_key = api_key or os.getenv("MISTRAL_API_KEY", "x2KYzd8Eb6YPoBAtMszeICnvVWmwQLzZ")
        
        self.client = MistralClient(api_key=api_key)
        self.model = "mistral-large-latest"
        
        print(f"✅ Mistral AI initialized (model: {self.model})")
    
    @property
    def chat(self):
        """Returns chat interface compatible with existing code"""
        return MistralChatWrapper(self.client, self.model)
    
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Direct generation method"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self.client.chat(
            model=self.model,
            messages=messages,
            temperature=0.2
        )
        
        return response.choices[0].message.content



class MistralChatWrapper:
    """Wrapper to maintain OpenAI-style API compatibility"""
    
    def __init__(self, client, model: str):
        self.client = client
        self.model = model
        self.completions = self
    
    def create(self, model=None, messages=None, **kwargs):
        """OpenAI-compatible create method"""
        # Convert OpenAI-style messages to Mistral format (dict)
        mistral_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                mistral_messages.append({"role": msg["role"], "content": msg["content"]})
            else:
                mistral_messages.append({"role": msg.role, "content": msg.content})
        
        # Extract parameters
        temperature = kwargs.get("temperature", 0.2)
        max_tokens = kwargs.get("max_tokens", 1000)
        
        # Call Mistral API
        response = self.client.chat(
            model=model or self.model,
            messages=mistral_messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response


# Global client
_client = None

def get_gemini_client():
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
