"""
Main FastAPI application for multimodal apparel search.
Handles all three search scenarios with a modern web interface.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import aiofiles

from app.config import settings
from app.services import azure_clients

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version="1.0.0"
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize Azure service clients on startup."""
    try:
        await azure_clients.initialize()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    await azure_clients.close()
    logger.info("Application shutdown completed")


def validate_image_file(file: UploadFile) -> None:
    """Validate uploaded image file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.allowed_image_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(settings.allowed_image_extensions)}"
        )
    
    # Check file size (FastAPI handles this automatically with File size limit)
    if file.size and file.size > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB"
        )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the main search interface."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "app_title": settings.app_title,
        "max_file_size": settings.max_file_size_mb,
        "allowed_extensions": ", ".join(settings.allowed_image_extensions)
    })


@app.post("/search/image")
async def search_by_image(
    image: UploadFile = File(..., description="Image file for search")
):
    """
    Scenario 1: Search for apparel using image input only.
    Uses Azure Computer Vision multimodal embeddings to get true image embedding and searches imageVector column.
    """
    try:
        # Validate image file
        validate_image_file(image)
        
        # Read image data
        image_data = await image.read()
        
        # Get multimodal image embedding using Azure Computer Vision
        logger.info("Generating multimodal image embedding...")
        embedding = await azure_clients.get_image_embedding(image_data)
        
        # Search using image vector
        logger.info("Searching by image vector...")
        results = await azure_clients.search_by_vector(embedding, "imageVector")
        
        return JSONResponse({
            "success": True,
            "search_type": "image",
            "results": results,
            "total_results": len(results)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Image search failed")


@app.post("/search/text")
async def search_by_text(
    query: str = Form(..., description="Text query for search")
):
    """
    Scenario 2: Search for apparel using text input only.
    Uses Azure Computer Vision multimodal embeddings to get text embedding compatible with image embeddings.
    """
    try:
        if not query.strip():
            raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
        # Primary: Vector search using multimodal text embedding
        logger.info(f"Generating multimodal text embedding for query: {query[:50]}...")
        embedding = await azure_clients.get_text_embedding(query)
        
        logger.info("Searching by vector similarity on imageVector field...")
        results = await azure_clients.search_by_vector(embedding, "imageVector")
        
        # Fallback: Traditional text search if vector search returns no results
        if len(results) == 0:
            logger.info("No results from vector search, falling back to traditional text search...")
            results = await azure_clients.search_by_text_integrated(query)
        
        return JSONResponse({
            "success": True,
            "search_type": "text",
            "query": query,
            "results": results,
            "total_results": len(results)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Text search failed")


@app.post("/search/multimodal")
async def search_multimodal(
    image: UploadFile = File(..., description="Image file for search"),
    query: str = Form(..., description="Text query for contextual search")
):
    """
    Scenario 3: Search using both image and text input.
    Uses GPT-4 Vision to analyze image with text context, then searches descriptionVector.
    """
    try:
        # Validate inputs
        validate_image_file(image)
        if not query.strip():
            raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
        # Read image data
        image_data = await image.read()
        
        # Analyze image with GPT-4 Vision using text context
        logger.info("Analyzing image with GPT-4 Vision...")
        enhanced_query = await azure_clients.analyze_image_with_gpt4v(image_data, query)
        
        # Get multimodal embedding for enhanced query
        logger.info("Generating multimodal embedding for enhanced query...")
        embedding = await azure_clients.get_text_embedding(enhanced_query)
        
        # Search using image vector
        logger.info("Searching by enhanced image vector...")
        results = await azure_clients.search_by_vector(embedding, "imageVector")
        
        return JSONResponse({
            "success": True,
            "search_type": "multimodal",
            "original_query": query,
            "enhanced_query": enhanced_query,
            "results": results,
            "total_results": len(results)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multimodal search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Multimodal search failed")


@app.post("/item/enhanced-description")
async def get_enhanced_description(request: dict):
    """
    Generate an enhanced, compelling description for an item using GPT-4o vision analysis.
    """
    try:
        # Validate required fields
        if "image_url" not in request:
            raise HTTPException(status_code=400, detail="image_url is required")
        
        image_url = request["image_url"]
        item_data = request.get("item_data", {})
        
        # Validate image URL
        if not image_url or not isinstance(image_url, str):
            raise HTTPException(status_code=400, detail="Valid image_url is required")
        
        # Get enhanced description from GPT-4o
        enhanced_description = await azure_clients.get_enhanced_item_description(
            image_url=image_url,
            item_data=item_data
        )
        
        return {
            "success": True,
            "enhanced_description": enhanced_description,
            "item_id": item_data.get("id", "unknown")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced description generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Enhanced description generation failed")


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "multimodal-search"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )