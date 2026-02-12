#!/usr/bin/env python3
"""
Real Embedding Provider - NO MOCKS
Uses actual OpenAI, Anthropic, or other embedding APIs
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.expanduser('~/.env'))


class EmbeddingProvider(Enum):
    """Supported embedding providers"""
    OLLAMA = "ollama"  # FREE - Local embeddings, no API costs
    OPENAI = "openai"
    ANTHROPIC = "anthropic"  # Note: Claude doesn't have embeddings, will use Voyage AI
    VOYAGE = "voyage"
    COHERE = "cohere"


@dataclass
class EmbeddingConfig:
    """Embedding configuration"""
    provider: EmbeddingProvider
    model: str
    dimension: int
    api_key: str
    base_url: Optional[str] = None
    max_batch_size: int = 100
    timeout: int = 30


class RealEmbeddingService:
    """
    Production embedding service with real API calls
    NO MOCK DATA - Uses actual embedding APIs
    """

    def __init__(
        self,
        provider: EmbeddingProvider = EmbeddingProvider.OLLAMA,  # Default to FREE local
        model: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize real embedding service

        Args:
            provider: Embedding provider to use (default: OLLAMA - free, local)
            model: Model name (uses default if None)
            api_key: API key (reads from env if None)
        """
        self.provider = provider

        # Configure based on provider
        if provider == EmbeddingProvider.OLLAMA:
            # FREE - No API key needed, runs locally via Ollama
            self.api_key = None
            self.model = model or 'nomic-embed-text'  # Free local embedding model
            self.dimension = 768  # nomic-embed-text dimension
            self.base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            print(f"🆓 Using FREE local Ollama embeddings: {self.model}")

        elif provider == EmbeddingProvider.OPENAI:
            self.api_key = api_key or os.getenv('OPENAI_API_KEY')
            self.model = model or 'text-embedding-ada-002'
            self.dimension = 1536
            self.base_url = 'https://api.openai.com/v1'

            if not self.api_key:
                raise ValueError("OpenAI API key not found in environment")

        elif provider == EmbeddingProvider.VOYAGE:
            # Anthropic recommends Voyage AI for embeddings
            self.api_key = api_key or os.getenv('VOYAGE_API_KEY')
            self.model = model or 'voyage-large-2'
            self.dimension = 1536
            self.base_url = 'https://api.voyageai.com/v1'

            if not self.api_key:
                raise ValueError("Voyage AI API key not found in environment")

        elif provider == EmbeddingProvider.COHERE:
            self.api_key = api_key or os.getenv('COHERE_API_KEY')
            self.model = model or 'embed-english-v3.0'
            self.dimension = 1024
            self.base_url = 'https://api.cohere.ai/v1'

            if not self.api_key:
                raise ValueError("Cohere API key not found in environment")

        else:
            raise ValueError(f"Unsupported provider: {provider}")

        self.client = httpx.AsyncClient(timeout=30.0)

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate real embedding for a single text

        Args:
            text: Text to embed

        Returns:
            Embedding vector (real API call, no mocks)
        """
        return (await self.embed_batch([text]))[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate real embeddings for multiple texts

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (real API calls)
        """
        if not texts:
            return []

        # Clean and validate inputs
        texts = [t.strip() for t in texts if t and t.strip()]
        if not texts:
            return []

        if self.provider == EmbeddingProvider.OLLAMA:
            return await self._embed_ollama(texts)
        elif self.provider == EmbeddingProvider.OPENAI:
            return await self._embed_openai(texts)
        elif self.provider == EmbeddingProvider.VOYAGE:
            return await self._embed_voyage(texts)
        elif self.provider == EmbeddingProvider.COHERE:
            return await self._embed_cohere(texts)
        else:
            raise ValueError(f"Provider {self.provider} not implemented")

    async def _embed_ollama(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings from Ollama (LOCAL - FREE)

        Real local API call - NO COST, no external API
        """
        url = f"{self.base_url}/api/embeddings"

        embeddings = []
        for text in texts:
            payload = {
                "model": self.model,
                "prompt": text
            }

            try:
                response = await self.client.post(url, json=payload)
                response.raise_for_status()

                data = response.json()
                embeddings.append(data['embedding'])

            except httpx.HTTPStatusError as e:
                raise Exception(f"Ollama API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise Exception(f"Failed to get Ollama embeddings: {str(e)}")

        return embeddings

    async def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings from OpenAI API (COSTS MONEY)

        Real API call - no simulation
        """
        url = f"{self.base_url}/embeddings"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "input": texts,
            "model": self.model,
            "encoding_format": "float"
        }

        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()

            # Extract embeddings in correct order
            embeddings = [None] * len(texts)
            for item in data['data']:
                embeddings[item['index']] = item['embedding']

            # Verify all embeddings were returned
            if None in embeddings:
                raise ValueError("Missing embeddings in OpenAI response")

            return embeddings

        except httpx.HTTPStatusError as e:
            raise Exception(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get OpenAI embeddings: {str(e)}")

    async def _embed_voyage(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings from Voyage AI API

        Real API call - no simulation
        """
        url = f"{self.base_url}/embeddings"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "input": texts,
            "model": self.model
        }

        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()
            return [item['embedding'] for item in data['data']]

        except httpx.HTTPStatusError as e:
            raise Exception(f"Voyage AI API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get Voyage embeddings: {str(e)}")

    async def _embed_cohere(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings from Cohere API

        Real API call - no simulation
        """
        url = f"{self.base_url}/embed"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "texts": texts,
            "model": self.model,
            "input_type": "search_document"
        }

        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()
            return data['embeddings']

        except httpx.HTTPStatusError as e:
            raise Exception(f"Cohere API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get Cohere embeddings: {str(e)}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Convenience function for quick embedding generation
async def get_embeddings(
    texts: List[str],
    provider: EmbeddingProvider = EmbeddingProvider.OLLAMA  # Default to FREE local
) -> List[List[float]]:
    """
    Quick function to get embeddings

    Args:
        texts: Texts to embed
        provider: Provider to use (default: OLLAMA - free, local, no API costs)

    Returns:
        List of embedding vectors (real API calls or local Ollama)
    """
    async with RealEmbeddingService(provider=provider) as service:
        return await service.embed_batch(texts)


# Example and test
async def test_real_embeddings():
    """Test real embedding generation - FREE local Ollama first"""
    print("🧪 Testing Real Embedding Service\n")

    # Test data
    texts = [
        "Kimi K2.5 can spawn up to 100 specialized sub-agents",
        "Python is a high-level programming language",
        "Machine learning models require training data"
    ]

    # Try Ollama first (FREE - no API costs!)
    try:
        print("🔹 Testing Ollama embeddings (FREE - Local)...")
        async with RealEmbeddingService(provider=EmbeddingProvider.OLLAMA) as service:
            embeddings = await service.embed_batch(texts)

            print(f"✅ Generated {len(embeddings)} embeddings (NO COST)")
            print(f"   Dimension: {len(embeddings[0])}")
            print(f"   Sample (first 5 values): {embeddings[0][:5]}")
            print(f"   Model: {service.model} (local, free)")
            print(f"   💰 Cost: $0.00 (runs locally!)\n")

    except Exception as e:
        print(f"❌ Ollama failed: {e}")
        print(f"   Make sure Ollama is running and model is pulled:")
        print(f"   ollama pull nomic-embed-text\n")

    # Try OpenAI if you want to compare (COSTS MONEY)
    try:
        print("🔹 Testing OpenAI embeddings (PAID API - costs money)...")
        async with RealEmbeddingService(provider=EmbeddingProvider.OPENAI) as service:
            embeddings = await service.embed_batch(texts[:1])  # Just one to save money

            print(f"✅ Generated {len(embeddings)} embeddings")
            print(f"   Dimension: {len(embeddings[0])}")
            print(f"   Sample (first 5 values): {embeddings[0][:5]}")
            print(f"   Model: {service.model}")
            print(f"   💰 Cost: ~$0.00013 per 1K tokens\n")

    except Exception as e:
        print(f"❌ OpenAI skipped (use Ollama for free!): {e}\n")


if __name__ == "__main__":
    asyncio.run(test_real_embeddings())
