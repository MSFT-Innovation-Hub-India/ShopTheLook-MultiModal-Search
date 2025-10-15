"""
Azure service clients using managed identity authentication.
Implements secure access to Azure AI Search, Computer Vision, and OpenAI services.
"""

import asyncio
import base64
import logging
from typing import List, Dict, Any, Optional
from io import BytesIO
import json

from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AsyncAzureOpenAI
from PIL import Image
import aiohttp

from .config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AzureServiceClients:
    """Manages Azure service clients with managed identity authentication."""
    
    def __init__(self):
        self.credential = None
        self.search_client = None
        self.openai_client = None
        self.http_session = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize all Azure service clients with managed identity."""
        if self._initialized:
            return
        
        try:
            # Initialize Azure Default Credentials (works with Managed Identity for Search & OpenAI)
            self.credential = DefaultAzureCredential()
            
            # Initialize Azure AI Search client
            # Use API key if provided, otherwise use Managed Identity (requires proper RBAC)
            if settings.azure_search_api_key:
                search_credential = AzureKeyCredential(settings.azure_search_api_key)
            else:
                search_credential = self.credential
                
            self.search_client = SearchClient(
                endpoint=settings.azure_search_service_endpoint,
                index_name=settings.azure_search_index_name,
                credential=search_credential
            )
            
            # Initialize HTTP session for Computer Vision multimodal embeddings API
            self.http_session = aiohttp.ClientSession()
            
            # Store Computer Vision credentials and endpoint for multimodal API calls
            self.vision_endpoint = settings.azure_computer_vision_endpoint.rstrip('/')
            self.vision_api_key = settings.azure_computer_vision_api_key
            
            # Initialize Azure OpenAI client with API key or Managed Identity
            if settings.azure_openai_api_key:
                # Use API key authentication
                self.openai_client = AsyncAzureOpenAI(
                    azure_endpoint=settings.azure_openai_endpoint,
                    api_key=settings.azure_openai_api_key,
                    api_version=settings.azure_oai_api_version
                )
                logger.info("Azure OpenAI client initialized with API key authentication")
            else:
                # Fallback to Managed Identity authentication
                openai_token_provider = get_bearer_token_provider(
                    self.credential,
                    "https://cognitiveservices.azure.com/.default"
                )
                self.openai_client = AsyncAzureOpenAI(
                    azure_endpoint=settings.azure_openai_endpoint,
                    azure_ad_token_provider=openai_token_provider,
                    api_version=settings.azure_oai_api_version
                )
                logger.info("Azure OpenAI client initialized with Managed Identity authentication")
            
            self._initialized = True
            logger.info("Azure service clients initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure clients: {str(e)}")
            raise
    
    async def cleanup(self):
        """Clean up resources."""
        if self.http_session:
            await self.http_session.close()
    
    async def get_image_embedding(self, image_data: bytes) -> List[float]:
        """
        Get image embedding using Azure Computer Vision Multimodal Embeddings API.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            List of floats representing the multimodal image embedding (1024 dimensions)
        """
        try:
            # Validate and process image
            image = Image.open(BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large (max 20MB for multimodal embeddings, but we'll keep it smaller for performance)
            max_size = (1024, 1024)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Convert back to bytes
            buffer = BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            processed_data = buffer.getvalue()
            
            # Call Azure Computer Vision multimodal embeddings API
            url = f"{self.vision_endpoint}/computervision/retrieval:vectorizeImage"
            
            headers = {
                "Content-Type": "application/octet-stream",
                "Ocp-Apim-Subscription-Key": self.vision_api_key
            }
            
            params = {
                "api-version": settings.azure_vision_api_version,
                "model-version": settings.azure_vision_model_version
            }
            
            async with self.http_session.post(url, headers=headers, params=params, data=processed_data) as response:
                if response.status == 200:
                    result = await response.json()
                    vector = result.get("vector", [])
                    
                    if len(vector) != 1024:
                        logger.warning(f"Expected 1024 dimensions, got {len(vector)}")
                    
                    logger.info(f"Multimodal image embedding generated successfully: {len(vector)} dimensions")
                    return vector
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to generate image embedding. Status: {response.status}, Error: {error_text}")
                    raise Exception(f"Computer Vision API error: {response.status} - {error_text}")
            
        except Exception as e:
            logger.error(f"Failed to get multimodal image embedding: {str(e)}")
            raise
    
    async def get_text_embedding(self, text: str) -> List[float]:
        """
        Get text embedding using Azure Computer Vision Multimodal Embeddings API.
        This ensures text and image embeddings are in the same vector space.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the multimodal text embedding (1024 dimensions)
        """
        try:
            # Validate text length (must be between 1-70 words)
            word_count = len(text.split())
            if word_count == 0:
                text = "clothing apparel fashion"
            elif word_count > 70:
                # Truncate to 70 words
                words = text.split()[:70]
                text = " ".join(words)
                logger.info(f"Text truncated to 70 words: {text}")
            
            # Call Azure Computer Vision multimodal embeddings API
            url = f"{self.vision_endpoint}/computervision/retrieval:vectorizeText"
            
            headers = {
                "Content-Type": "application/json",
                "Ocp-Apim-Subscription-Key": self.vision_api_key
            }
            
            params = {
                "api-version": settings.azure_vision_api_version,
                "model-version": settings.azure_vision_model_version
            }
            
            payload = {
                "text": text
            }
            
            async with self.http_session.post(url, headers=headers, params=params, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    vector = result.get("vector", [])
                    
                    if len(vector) != 1024:
                        logger.warning(f"Expected 1024 dimensions, got {len(vector)}")
                    
                    logger.info(f"Multimodal text embedding generated successfully: text='{text[:50]}...', dimensions={len(vector)}")
                    return vector
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to generate text embedding. Status: {response.status}, Error: {error_text}")
                    raise Exception(f"Computer Vision API error: {response.status} - {error_text}")
            
        except Exception as e:
            logger.error(f"Failed to get multimodal text embedding: {str(e)}")
            raise
    
    async def analyze_image_with_gpt4v(self, image_data: bytes, text_prompt: str) -> str:
        """
        Analyze image with GPT-4 Vision based on text prompt.
        
        Args:
            image_data: Raw image bytes
            text_prompt: Text context for image analysis
            
        Returns:
            Generated search criteria text
        """
        try:
            # Convert image to base64
            image_b64 = base64.b64encode(image_data).decode()
            
            # Create messages for GPT-4V
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""Analyze this image in the context of: "{text_prompt}"
                            
Generate a detailed search query that combines the visual elements you see in the image 
with the user's text input. Focus on apparel attributes like:
- Colors, patterns, textures
- Clothing type and style
- Materials and fabric
- Seasonal appropriateness
- Occasion or use case

Provide a concise but descriptive search query (max 100 words) that would help find similar items in an apparel catalog."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]
            
            response = await self.openai_client.chat.completions.create(
                model=settings.azure_oai_deployment,
                messages=messages,
                max_tokens=200,
                temperature=0.3
            )
            
            generated_query = response.choices[0].message.content.strip()
            logger.info(f"GPT-4V analysis completed. Generated query length: {len(generated_query)}")
            return generated_query
            
        except Exception as e:
            logger.error(f"Failed to analyze image with GPT-4V: {str(e)}")
            raise
    
    async def get_enhanced_item_description(self, image_url: str, item_data: Dict[str, Any]) -> str:
        """
        Generate an enhanced, compelling description for an item using GPT-4o vision analysis.
        
        Args:
            image_url: URL of the item image
            item_data: Item data with attributes like brand, category, price, etc.
            
        Returns:
            Enhanced description highlighting unique aspects and fashion statement
        """
        try:
            # Create detailed prompt for fashion analysis
            prompt = f"""Analyze this fashion item and create a well-structured, formatted description.

Basic Info: {item_data.get('description', 'Fashion item')} - ${item_data.get('price', 'N/A')}

Format your response exactly like this structure with clear headings and bullet points:

**🎨 Visual Design**
• Color palette and pattern details
• Fabric texture and material appearance
• Key design elements and silhouette

**✨ Style Statement**
• Fashion category and aesthetic
• What mood/personality it conveys
• Style inspiration or theme

**👔 Versatility & Occasions**
• Casual wear scenarios
• Professional/formal possibilities
• Seasonal appropriateness

**🔥 Standout Features**
• Unique design details
• Quality indicators visible
• What makes it special

**💡 Styling Tips**
• How to pair with other pieces
• Accessories that complement
• Target fashion demographic

Keep each bullet point concise (1-2 lines) and engaging. Use fashion-forward language that makes the item sound desirable."""

            # Create messages for GPT-4V
            messages = [
                {
                    "role": "user", 
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url,
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]
            
            response = await self.openai_client.chat.completions.create(
                model=settings.azure_oai_deployment,
                messages=messages,
                max_tokens=300,
                temperature=0.7  # Slightly higher temperature for creative descriptions
            )
            
            enhanced_description = response.choices[0].message.content.strip()
            logger.info(f"Enhanced description generated for item {item_data.get('id', 'unknown')}")
            return enhanced_description
            
        except Exception as e:
            logger.error(f"Failed to generate enhanced description: {str(e)}")
            # Return a fallback description if GPT-4V fails
            return f"A stylish {item_data.get('category', 'fashion item')} from {item_data.get('brand', 'a premium brand')} that combines quality craftsmanship with contemporary design. Perfect for adding a touch of sophistication to your wardrobe."
    
    async def search_by_vector(self, embedding: List[float], vector_field: str) -> List[Dict[str, Any]]:
        """
        Search Azure AI Search index using vector similarity.
        
        Args:
            embedding: Vector embedding for search
            vector_field: Field name to search against (imageVector or descriptionVector)
            
        Returns:
            List of search results
        """
        try:
            # Create vectorized query
            vector_query = VectorizedQuery(
                vector=embedding,
                k_nearest_neighbors=settings.search_top_k,
                fields=vector_field
            )
            
            # Execute search
            results = await self.search_client.search(
                search_text="",
                vector_queries=[vector_query],
                select=["id", "description", "img", "price"],
                top=settings.search_top_k
            )
            
            # Convert results to list
            search_results = []
            async for result in results:
                # Lower the threshold to get more results initially
                if result.get("@search.score", 0) >= 0.01:  # Much lower threshold
                    search_results.append({
                        "id": result.get("id"),
                        "description": result.get("description", ""),
                        "image_url": result.get("img", ""),
                        "price": result.get("price", 0),
                        "category": result.get("category", "N/A"),
                        "brand": result.get("brand", "N/A"),
                        "color": result.get("color", "N/A"),
                        "size": result.get("size", "N/A"),
                        "material": result.get("material", "N/A"),
                        "season": result.get("season", "N/A"),
                        "score": result.get("@search.score", 0)
                    })
            
            # Sort results by relevancy score in descending order
            search_results.sort(key=lambda x: x["score"], reverse=True)
            
            logger.info(f"Search completed. Found {len(search_results)} results above threshold, sorted by relevancy")
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to search by vector: {str(e)}")
            raise
            
    async def search_by_text_integrated(self, text: str) -> List[Dict[str, Any]]:
        """
        Search using integrated vectorization (like Azure portal search playground).
        This uses the search service's built-in vectorization instead of manual embeddings.
        
        Args:
            text: Search text
            
        Returns:
            List of search results
        """
        try:
            # Use integrated text search with vectorization
            # This approach is similar to what works in the Azure portal
            results = await self.search_client.search(
                search_text=text,
                search_fields=["description"],  # Search in text fields
                select=["id", "description", "img", "price"],
                top=settings.search_top_k,
                include_total_count=True
            )
            
            # Convert results to list
            search_results = []
            async for result in results:
                search_results.append({
                    "id": result.get("id"),
                    "description": result.get("description", ""),
                    "image_url": result.get("img", ""),
                    "price": result.get("price", 0),
                    "category": result.get("category", "N/A"),
                    "brand": result.get("brand", "N/A"),
                    "color": result.get("color", "N/A"),
                    "size": result.get("size", "N/A"),
                    "material": result.get("material", "N/A"),
                    "season": result.get("season", "N/A"),
                    "score": result.get("@search.score", 0)
                })
            
            # Sort results by relevancy score in descending order
            search_results.sort(key=lambda x: x["score"], reverse=True)
            
            logger.info(f"Text search completed. Found {len(search_results)} results, sorted by relevancy")
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to search by text: {str(e)}")
            raise
    
    async def close(self):
        """Clean up resources."""
        if self.search_client:
            await self.search_client.close()
        if self.http_session:
            await self.http_session.close()
        if self.credential:
            await self.credential.close()


# Global service clients instance
azure_clients = AzureServiceClients()