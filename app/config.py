"""
Configuration management for the multimodal search application.
Uses Azure Default Credentials for secure authentication.
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Azure OpenAI Configuration
    azure_openai_endpoint: str
    azure_oai_deployment: str
    azure_openai_embedding_model: str
    azure_oai_api_version: str
    
    # Azure Computer Vision Configuration
    azure_computer_vision_endpoint: str
    azure_computer_vision_api_key: str
    
    # Azure AI Vision Multimodal Embeddings Configuration
    azure_vision_api_version: str = "2024-02-01"
    azure_vision_model_version: str = "2023-04-15"
    
    # Azure AI Search Configuration
    azure_search_service_endpoint: str
    azure_search_index_name: str
    azure_search_api_key: Optional[str] = None
    
    # Application Configuration
    app_title: str = "Multimodal Apparel Search"
    app_description: str = "Search for apparel using text and images powered by Azure AI"
    max_file_size_mb: int = 10
    allowed_image_extensions: list = [".jpg", ".jpeg", ".png", ".webp", ".bmp"]
    
    # Search Configuration
    search_top_k: int = 12
    similarity_threshold: float = 0.1  # Lower threshold to get more results
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()