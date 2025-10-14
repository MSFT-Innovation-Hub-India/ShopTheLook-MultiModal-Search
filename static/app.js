/**
 * JavaScript for the multimodal apparel search application
 * Handles UI interactions, file uploads, and API calls for all search scenarios
 */

class MultimodalSearchApp {
    constructor() {
        this.currentSearchType = 'image';
        this.init();
    }

    init() {
        this.bindEvents();
        this.setupImageUploads();
        this.setupFormSubmissions();
    }

    bindEvents() {
        // Clear results button
        document.getElementById('clearResults').addEventListener('click', () => {
            this.clearResults();
        });

        // Tab switching
        const tabs = document.querySelectorAll('[data-bs-toggle="pill"]');
        tabs.forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                this.currentSearchType = e.target.id.replace('-tab', '');
            });
        });
    }

    setupImageUploads() {
        // Setup for regular image search
        this.setupImageUpload(
            'imageUploadArea',
            'imageFile',
            'imagePreview',
            'previewImg',
            'removeImage',
            'imageSearchBtn'
        );

        // Setup for multimodal image search
        this.setupImageUpload(
            'multimodalImageUploadArea',
            'multimodalImageFile',
            'multimodalImagePreview',
            'multimodalPreviewImg',
            'removeMultimodalImage',
            'multimodalSearchBtn'
        );
    }

    setupImageUpload(uploadAreaId, fileInputId, previewId, previewImgId, removeButtonId, submitButtonId) {
        const uploadArea = document.getElementById(uploadAreaId);
        const fileInput = document.getElementById(fileInputId);
        const preview = document.getElementById(previewId);
        const previewImg = document.getElementById(previewImgId);
        const removeButton = document.getElementById(removeButtonId);
        const submitButton = document.getElementById(submitButtonId);

        // Click to upload
        uploadArea.addEventListener('click', () => {
            if (!preview.style.display || preview.style.display === 'none') {
                fileInput.click();
            }
        });

        // File selection
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.handleImageUpload(file, preview, previewImg, uploadArea, submitButton);
            }
        });

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const file = files[0];
                if (this.isValidImageFile(file)) {
                    fileInput.files = files;
                    this.handleImageUpload(file, preview, previewImg, uploadArea, submitButton);
                } else {
                    this.showError('Please select a valid image file (JPG, PNG, WebP, BMP)');
                }
            }
        });

        // Remove image
        removeButton.addEventListener('click', (e) => {
            e.stopPropagation();
            this.removeImage(fileInput, preview, uploadArea, submitButton);
        });
    }

    handleImageUpload(file, preview, previewImg, uploadArea, submitButton) {
        if (!this.isValidImageFile(file)) {
            this.showError('Please select a valid image file (JPG, PNG, WebP, BMP)');
            return;
        }

        if (file.size > 10 * 1024 * 1024) { // 10MB limit
            this.showError('File size must be less than 10MB');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            preview.style.display = 'block';
            uploadArea.querySelector('.upload-placeholder').style.display = 'none';
            submitButton.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    removeImage(fileInput, preview, uploadArea, submitButton) {
        fileInput.value = '';
        preview.style.display = 'none';
        uploadArea.querySelector('.upload-placeholder').style.display = 'block';
        submitButton.disabled = true;
    }

    isValidImageFile(file) {
        const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/bmp'];
        return validTypes.includes(file.type);
    }

    setupFormSubmissions() {
        // Image search form
        document.getElementById('imageSearchForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleImageSearch();
        });

        // Text search form
        document.getElementById('textSearchForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleTextSearch();
        });

        // Multimodal search form
        document.getElementById('multimodalSearchForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleMultimodalSearch();
        });
    }

    async handleImageSearch() {
        const fileInput = document.getElementById('imageFile');
        const file = fileInput.files[0];

        if (!file) {
            this.showError('Please select an image file');
            return;
        }

        const formData = new FormData();
        formData.append('image', file);

        try {
            this.showLoading('Analyzing image and searching for similar items...');
            
            const response = await fetch('/search/image', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Search failed');
            }

            this.displayResults(result);
        } catch (error) {
            this.showError(error.message);
        }
    }

    async handleTextSearch() {
        const query = document.getElementById('textQuery').value.trim();

        if (!query) {
            this.showError('Please enter a search query');
            return;
        }

        const formData = new FormData();
        formData.append('query', query);

        try {
            this.showLoading('Processing your query and searching...');
            
            const response = await fetch('/search/text', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Search failed');
            }

            this.displayResults(result);
        } catch (error) {
            this.showError(error.message);
        }
    }

    async handleMultimodalSearch() {
        const fileInput = document.getElementById('multimodalImageFile');
        const file = fileInput.files[0];
        const query = document.getElementById('multimodalQuery').value.trim();

        if (!file) {
            this.showError('Please select an image file');
            return;
        }

        if (!query) {
            this.showError('Please provide context or a search query');
            return;
        }

        const formData = new FormData();
        formData.append('image', file);
        formData.append('query', query);

        try {
            this.showLoading('Analyzing image with AI and generating enhanced search...');
            
            const response = await fetch('/search/multimodal', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Search failed');
            }

            this.displayResults(result);
        } catch (error) {
            this.showError(error.message);
        }
    }

    showLoading(message = 'Searching...') {
        document.getElementById('welcomeState').style.display = 'none';
        document.getElementById('resultsContainer').style.display = 'none';
        document.getElementById('errorState').style.display = 'none';
        document.getElementById('loadingState').style.display = 'block';
        
        const loadingText = document.querySelector('#loadingState h5');
        if (loadingText) {
            loadingText.textContent = message;
        }
    }

    displayResults(result) {
        // Hide other states
        document.getElementById('welcomeState').style.display = 'none';
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('errorState').style.display = 'none';

        // Show results container
        document.getElementById('resultsContainer').style.display = 'block';
        document.getElementById('clearResults').style.display = 'block';

        // Update title and count
        document.getElementById('resultsTitle').textContent = this.getResultsTitle(result.search_type);
        document.getElementById('resultCount').textContent = `${result.total_results} items`;

        // Show enhanced query for multimodal search
        const enhancedQueryDiv = document.getElementById('enhancedQuery');
        if (result.search_type === 'multimodal' && result.enhanced_query) {
            document.getElementById('enhancedQueryText').textContent = result.enhanced_query;
            enhancedQueryDiv.style.display = 'block';
        } else {
            enhancedQueryDiv.style.display = 'none';
        }

        // Generate results grid
        const resultsGrid = document.getElementById('resultsGrid');
        resultsGrid.innerHTML = '';

        if (result.results.length === 0) {
            resultsGrid.innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="bi bi-search display-4 text-muted"></i>
                    <h5 class="text-muted mt-3">No results found</h5>
                    <p class="text-muted">Try adjusting your search criteria or use a different image.</p>
                </div>
            `;
        } else {
            result.results.forEach((item, index) => {
                const resultCard = this.createResultCard(item, index);
                resultsGrid.appendChild(resultCard);
            });
        }

        // Add fade-in animation
        resultsGrid.classList.add('fade-in');
    }

    createResultCard(item, index) {
        const col = document.createElement('div');
        col.className = 'col-md-4 col-lg-3 mb-4';
        
        col.innerHTML = `
            <div class="card result-card">
                <div class="position-relative">
                    <img src="${item.image_url || '/static/placeholder-image.png'}" 
                         class="card-img-top" 
                         alt="${item.description || 'Product image'}"
                         onerror="this.src='/static/placeholder-image.png'">
                    <span class="score-badge" title="Relevancy Score: ${item.score.toFixed(2)}">${this.formatRelevancyScore(item.score)}</span>
                </div>
                <div class="card-body">
                    <h6 class="card-title mb-2">${this.truncateText(item.description || 'No description', 60)}</h6>
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="price-tag">$${item.price || '0.00'}</span>
                        <small class="text-muted">ID: ${item.id || 'N/A'}</small>
                    </div>
                </div>
            </div>
        `;

        // Add click handler for more details (if needed)
        col.addEventListener('click', () => {
            this.showItemDetails(item);
        });

        return col;
    }

    async showItemDetails(item) {
        // Populate modal with item details
        document.getElementById('modalItemImage').src = item.image_url || '/static/placeholder-image.png';
        document.getElementById('modalItemTitle').textContent = item.description || 'No description available';
        document.getElementById('modalScoreBadge').textContent = this.formatRelevancyScore(item.score);
        document.getElementById('modalItemPrice').textContent = `$${item.price || '0.00'}`;
        document.getElementById('modalItemRelevance').textContent = this.formatRelevancyScore(item.score);
        document.getElementById('modalItemId').textContent = item.id || 'N/A';
        
        // Reset enhanced description state
        document.getElementById('enhancedDescriptionLoading').style.display = 'block';
        document.getElementById('enhancedDescription').style.display = 'none';
        document.getElementById('enhancedDescriptionError').style.display = 'none';
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('itemDetailModal'));
        modal.show();
        
        // Fetch enhanced description from GPT-4o
        try {
            const response = await fetch('/item/enhanced-description', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    image_url: item.image_url,
                    item_data: item
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                document.getElementById('enhancedDescriptionLoading').style.display = 'none';
                const formattedDescription = this.formatAIDescription(result.enhanced_description);
                document.getElementById('enhancedDescription').innerHTML = formattedDescription;
                document.getElementById('enhancedDescription').style.display = 'block';
            } else {
                throw new Error(result.detail || 'Failed to generate description');
            }
        } catch (error) {
            console.error('Failed to fetch enhanced description:', error);
            document.getElementById('enhancedDescriptionLoading').style.display = 'none';
            document.getElementById('enhancedDescriptionError').style.display = 'block';
        }
    }

    getResultsTitle(searchType) {
        switch (searchType) {
            case 'image':
                return 'Similar Items Found';
            case 'text':
                return 'Text Search Results';
            case 'multimodal':
                return 'AI-Enhanced Results';
            default:
                return 'Search Results';
        }
    }

    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    formatRelevancyScore(score) {
        // Display the actual relevancy score with appropriate formatting
        if (score >= 1) {
            return `${score.toFixed(1)}★`;  // Show as rating-style for scores >= 1
        } else {
            return `${(score * 100).toFixed(0)}%`;  // Show as percentage for scores < 1
        }
    }

    formatAIDescription(text) {
        // Convert the structured AI response to HTML with proper formatting
        let formatted = text;
        
        // Convert **bold text** to HTML bold with icons
        formatted = formatted.replace(/\*\*(🎨 Visual Design)\*\*/g, '<h6 class="ai-section-header"><i class="bi bi-palette-fill me-2"></i>$1</h6>');
        formatted = formatted.replace(/\*\*(✨ Style Statement)\*\*/g, '<h6 class="ai-section-header"><i class="bi bi-star-fill me-2"></i>$1</h6>');
        formatted = formatted.replace(/\*\*(👔 Versatility & Occasions)\*\*/g, '<h6 class="ai-section-header"><i class="bi bi-calendar-event me-2"></i>$1</h6>');
        formatted = formatted.replace(/\*\*(🔥 Standout Features)\*\*/g, '<h6 class="ai-section-header"><i class="bi bi-gem me-2"></i>$1</h6>');
        formatted = formatted.replace(/\*\*(💡 Styling Tips)\*\*/g, '<h6 class="ai-section-header"><i class="bi bi-lightbulb-fill me-2"></i>$1</h6>');
        
        // Convert bullet points to HTML lists
        const sections = formatted.split(/(?=<h6)/);
        
        return sections.map(section => {
            if (section.includes('<h6')) {
                // This is a section with a header
                const lines = section.split('\n');
                const header = lines[0];
                const bullets = lines.slice(1).filter(line => line.trim().startsWith('•'));
                
                if (bullets.length > 0) {
                    const listItems = bullets.map(bullet => 
                        `<li>${bullet.replace('•', '').trim()}</li>`
                    ).join('');
                    
                    return `${header}<ul class="ai-bullet-list">${listItems}</ul>`;
                } else {
                    return section;
                }
            } else {
                return section;
            }
        }).join('');
    }

    showError(message) {
        document.getElementById('welcomeState').style.display = 'none';
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('resultsContainer').style.display = 'none';
        
        document.getElementById('errorMessage').textContent = message;
        document.getElementById('errorState').style.display = 'block';
    }

    clearResults() {
        // Reset all forms
        document.getElementById('imageSearchForm').reset();
        document.getElementById('textSearchForm').reset();
        document.getElementById('multimodalSearchForm').reset();

        // Remove image previews
        this.removeImage(
            document.getElementById('imageFile'),
            document.getElementById('imagePreview'),
            document.getElementById('imageUploadArea'),
            document.getElementById('imageSearchBtn')
        );

        this.removeImage(
            document.getElementById('multimodalImageFile'),
            document.getElementById('multimodalImagePreview'),
            document.getElementById('multimodalImageUploadArea'),
            document.getElementById('multimodalSearchBtn')
        );

        // Show welcome state
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('resultsContainer').style.display = 'none';
        document.getElementById('errorState').style.display = 'none';
        document.getElementById('clearResults').style.display = 'none';
        document.getElementById('welcomeState').style.display = 'block';

        // Reset to first tab
        const firstTab = document.getElementById('image-tab');
        const bootstrap = window.bootstrap || window.Bootstrap;
        if (bootstrap && bootstrap.Tab) {
            const tabInstance = new bootstrap.Tab(firstTab);
            tabInstance.show();
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new MultimodalSearchApp();
});