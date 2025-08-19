
// Enhanced Shop Functionality
class ShopManager {
    constructor() {
        this.products = [];
        this.filteredProducts = [];
        this.cart = [];
        this.currentPage = 1;
        this.itemsPerPage = 12;
        this.filters = {
            category: 'all',
            priceRange: 1000,
            brands: [],
            ratings: [],
            search: ''
        };
        this.sortBy = 'featured';
        this.viewMode = 'grid';
        
        this.init();
    }
    
    init() {
        this.loadProducts();
        this.loadCartFromStorage();
        this.bindEvents();
        this.filters.category = 'weapons'; // Set default category
        this.updateFilters();
        this.renderProducts();
        this.updateCartUI();
        this.handleURLParams();
    }
    
    loadProducts() {
        // STK Supply Product Catalog
        this.products = [
            // Weapons
            {
                id: 1,
                name: "Street Arsenal - Safe",
                price: 3.00,
                category: "weapons",
                brand: "STK Supply",
                description: "Essential gear for the streets • Fully, buttons, switches, binary, AR9",
                image: "🔫",
                rating: 4.9,
                reviews: 234,
                inStock: true,
                featured: true,
                tags: ["arsenal", "safe", "street", "gear"],
                subcategory: "safe"
            },
            {
                id: 2,
                name: "Street Arsenal - Bag",
                price: 2.00,
                category: "weapons",
                brand: "STK Supply",
                description: "Premium setups • Custom builds • Street ready",
                image: "🎒",
                rating: 4.8,
                reviews: 189,
                inStock: true,
                featured: true,
                tags: ["arsenal", "bag", "storage"],
                subcategory: "bag"
            },
            {
                id: 3,
                name: "Street Arsenal - Trunk",
                price: 1.00,
                category: "weapons",
                brand: "STK Supply",
                description: "Pick from dropdown below • Select storage type for your weapon",
                image: "📦",
                rating: 4.7,
                reviews: 156,
                inStock: true,
                featured: false,
                tags: ["arsenal", "trunk", "storage"],
                subcategory: "trunk"
            },
            // Money
            {
                id: 4,
                name: "Max Money 990k",
                price: 1.00,
                category: "money",
                brand: "STK Supply",
                description: "Clean money packages • Regular & Gamepass options",
                image: "💰",
                rating: 4.9,
                reviews: 567,
                inStock: true,
                featured: true,
                tags: ["money", "package", "regular"],
                subcategory: "regular"
            },
            {
                id: 5,
                name: "Max Bank 990k",
                price: 1.00,
                category: "money",
                brand: "STK Supply",
                description: "Max out your cash • Clean money packages",
                image: "🏦",
                rating: 4.8,
                reviews: 432,
                inStock: true,
                featured: true,
                tags: ["money", "bank", "regular"],
                subcategory: "regular"
            },
            {
                id: 6,
                name: "Max Money 1.6M (Gamepass)",
                price: 2.00,
                category: "money",
                brand: "STK Supply",
                description: "Gamepass exclusive • Higher limits available",
                image: "💎",
                rating: 4.9,
                reviews: 321,
                inStock: true,
                featured: true,
                tags: ["money", "gamepass", "premium"],
                subcategory: "gamepass"
            },
            {
                id: 7,
                name: "Max Bank 1.6M (Gamepass)",
                price: 2.00,
                category: "money",
                brand: "STK Supply",
                description: "Gamepass bank package • Premium service",
                image: "💳",
                rating: 4.8,
                reviews: 289,
                inStock: true,
                featured: true,
                tags: ["money", "gamepass", "bank"],
                subcategory: "gamepass"
            },
            // Watches
            {
                id: 8,
                name: "Luxury Watch Collection",
                price: 1.00,
                category: "watches",
                brand: "STK Supply",
                description: "High-end connections • Watches & Scripts • Designer pieces • Custom codes",
                image: "⌚",
                rating: 4.9,
                reviews: 178,
                inStock: true,
                featured: true,
                tags: ["luxury", "watches", "designer"],
                subcategory: "luxury"
            },
            // Scripts
            {
                id: 9,
                name: "Custom Scripts Collection",
                price: 0.00,
                category: "scripts",
                brand: "STK Supply",
                description: "Coming Soon • Advanced automation scripts • Custom development",
                image: "💻",
                rating: 0,
                reviews: 0,
                inStock: false,
                featured: false,
                tags: ["scripts", "automation", "custom"],
                subcategory: "coming-soon"
            },
            ];
        
        this.filteredProducts = [...this.products];
    }
    
    bindEvents() {
        // Category tabs
        document.querySelectorAll('.category-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const category = e.currentTarget.dataset.category;
                
                // Update active tab
                document.querySelectorAll('.category-tab').forEach(t => t.classList.remove('active'));
                e.currentTarget.classList.add('active');
                
                // Update filter
                this.filters.category = category;
                this.applyFilters();
            });
        });
        
        // Price range
        const priceRange = document.getElementById('priceRange');
        const priceValue = document.getElementById('priceValue');
        const minPrice = document.getElementById('minPrice');
        const maxPrice = document.getElementById('maxPrice');
        
        if (priceRange) {
            priceRange.addEventListener('input', (e) => {
                this.filters.priceRange = parseInt(e.target.value);
                priceValue.textContent = this.filters.priceRange;
                this.applyFilters();
            });
        }
        
        if (minPrice && maxPrice) {
            [minPrice, maxPrice].forEach(input => {
                input.addEventListener('input', () => {
                    this.filters.minPrice = parseInt(minPrice.value) || 0;
                    this.filters.maxPrice = parseInt(maxPrice.value) || Infinity;
                    this.applyFilters();
                });
            });
        }
        
        // Brand filters
        document.querySelectorAll('input[type="checkbox"][value^="brand"]').forEach(input => {
            input.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.filters.brands.push(e.target.value);
                } else {
                    this.filters.brands = this.filters.brands.filter(brand => brand !== e.target.value);
                }
                this.applyFilters();
            });
        });
        
        // Rating filters
        document.querySelectorAll('input[type="checkbox"][value^="rating"]').forEach(input => {
            input.addEventListener('change', (e) => {
                const rating = parseInt(e.target.value);
                if (e.target.checked) {
                    this.filters.ratings.push(rating);
                } else {
                    this.filters.ratings = this.filters.ratings.filter(r => r !== rating);
                }
                this.applyFilters();
            });
        });
        
        // Sort
        const sortSelect = document.getElementById('sortSelect');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                this.sortBy = e.target.value;
                this.sortProducts();
                this.renderProducts();
            });
        }
        
        // View toggle
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.viewMode = e.target.dataset.view;
                this.renderProducts();
            });
        });
        
        // Search
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filters.search = e.target.value.toLowerCase();
                this.applyFilters();
                this.showSearchSuggestions(e.target.value);
            });
            
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.applyFilters();
                    this.hideSearch();
                }
            });
        }
    }
    
    handleURLParams() {
        const urlParams = new URLSearchParams(window.location.search);
        const category = urlParams.get('category');
        
        if (category && category !== 'all') {
            this.filters.category = category;
            const categoryInput = document.querySelector(`input[name="category"][value="${category}"]`);
            if (categoryInput) {
                categoryInput.checked = true;
            }
            this.applyFilters();
        }
    }
    
    applyFilters() {
        this.filteredProducts = this.products.filter(product => {
            // Category filter
            if (this.filters.category && product.category !== this.filters.category) {
                return false;
            }
            
            // Price filter
            if (product.price > this.filters.priceRange) {
                return false;
            }
            
            // Min/Max price filter
            if (this.filters.minPrice && product.price < this.filters.minPrice) {
                return false;
            }
            if (this.filters.maxPrice && product.price > this.filters.maxPrice) {
                return false;
            }
            
            // Brand filter
            if (this.filters.brands.length > 0 && !this.filters.brands.includes(product.brand)) {
                return false;
            }
            
            // Rating filter
            if (this.filters.ratings.length > 0) {
                const hasMatchingRating = this.filters.ratings.some(rating => {
                    if (rating === 5) return product.rating >= 4.5;
                    if (rating === 4) return product.rating >= 4.0;
                    return product.rating >= rating;
                });
                if (!hasMatchingRating) return false;
            }
            
            // Search filter
            if (this.filters.search) {
                const searchTerm = this.filters.search.toLowerCase();
                return product.name.toLowerCase().includes(searchTerm) ||
                       product.description.toLowerCase().includes(searchTerm) ||
                       product.tags.some(tag => tag.includes(searchTerm));
            }
            
            return true;
        });
        
        this.currentPage = 1;
        this.sortProducts();
        this.renderProducts();
        this.updateFilterCounts();
    }
    
    sortProducts() {
        switch (this.sortBy) {
            case 'price-low':
                this.filteredProducts.sort((a, b) => a.price - b.price);
                break;
            case 'price-high':
                this.filteredProducts.sort((a, b) => b.price - a.price);
                break;
            case 'name':
                this.filteredProducts.sort((a, b) => a.name.localeCompare(b.name));
                break;
            case 'newest':
                this.filteredProducts.sort((a, b) => b.id - a.id);
                break;
            case 'rating':
                this.filteredProducts.sort((a, b) => b.rating - a.rating);
                break;
            default:
                // Featured products first
                this.filteredProducts.sort((a, b) => {
                    if (a.featured && !b.featured) return -1;
                    if (!a.featured && b.featured) return 1;
                    return b.rating - a.rating;
                });
        }
    }
    
    renderProducts() {
        const container = document.getElementById('productsGrid');
        const loading = document.getElementById('loading');
        const noResults = document.getElementById('noResults');
        const resultsCount = document.getElementById('resultsCount');
        
        if (!container) return;
        
        // Update results count
        if (resultsCount) {
            const total = this.filteredProducts.length;
            resultsCount.textContent = `${total} product${total !== 1 ? 's' : ''}`;
        }
        
        // Show loading
        if (loading) loading.style.display = 'flex';
        if (noResults) noResults.style.display = 'none';
        container.innerHTML = '';
        
        setTimeout(() => {
            if (loading) loading.style.display = 'none';
            
            if (this.filteredProducts.length === 0) {
                if (noResults) noResults.style.display = 'block';
                return;
            }
            
            // Pagination
            const startIndex = (this.currentPage - 1) * this.itemsPerPage;
            const endIndex = startIndex + this.itemsPerPage;
            const paginatedProducts = this.filteredProducts.slice(startIndex, endIndex);
            
            container.className = this.viewMode === 'list' ? 'products-list' : 'products-grid';
            
            container.innerHTML = paginatedProducts.map(product => 
                this.createProductCard(product)
            ).join('');
            
            this.renderPagination();
        }, 300);
    }
    
    createProductCard(product) {
        const discountPercentage = product.originalPrice ? 
            Math.round(((product.originalPrice - product.price) / product.originalPrice) * 100) : 0;
        
        return `
            <div class="product-card" data-product-id="${product.id}">
                <div class="product-image">
                    ${product.image}
                    ${discountPercentage > 0 ? `<div class="discount-badge">-${discountPercentage}%</div>` : ''}
                    <div class="product-actions">
                        <button class="action-btn" onclick="shopManager.toggleWishlist(${product.id})" title="Add to Wishlist">
                            <i class="far fa-heart"></i>
                        </button>
                        <button class="action-btn" onclick="shopManager.quickView(${product.id})" title="Quick View">
                            <i class="fas fa-eye"></i>
                        </button>
                    </div>
                </div>
                <div class="product-info">
                    <div class="product-category">${product.category}</div>
                    <h3 class="product-title">${product.name}</h3>
                    <div class="product-rating">
                        <div class="stars">
                            ${this.renderStars(product.rating)}
                        </div>
                        <span class="rating-count">(${product.reviews})</span>
                    </div>
                    <div class="product-price">
                        $${product.price.toFixed(2)}
                        ${product.originalPrice ? `<span class="original-price">$${product.originalPrice.toFixed(2)}</span>` : ''}
                    </div>
                    ${product.inStock ? 
                        `<button class="add-to-cart" onclick="shopManager.addToCart(${product.id})">
                            <i class="fas fa-shopping-cart"></i>
                            Add to Cart
                        </button>` :
                        `<button class="add-to-cart coming-soon" disabled>
                            <i class="fas fa-clock"></i>
                            Coming Soon
                        </button>`
                    }
                </div>
            </div>
        `;
    }
    
    renderStars(rating) {
        const fullStars = Math.floor(rating);
        const hasHalfStar = rating % 1 !== 0;
        const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
        
        return [
            ...Array(fullStars).fill('<i class="fas fa-star"></i>'),
            hasHalfStar ? '<i class="fas fa-star-half-alt"></i>' : '',
            ...Array(emptyStars).fill('<i class="far fa-star"></i>')
        ].join('');
    }
    
    renderPagination() {
        const paginationContainer = document.getElementById('pagination');
        if (!paginationContainer) return;
        
        const totalPages = Math.ceil(this.filteredProducts.length / this.itemsPerPage);
        
        if (totalPages <= 1) {
            paginationContainer.innerHTML = '';
            return;
        }
        
        let paginationHTML = '';
        
        // Previous button
        paginationHTML += `
            <button ${this.currentPage === 1 ? 'disabled' : ''} 
                    onclick="shopManager.goToPage(${this.currentPage - 1})">
                <i class="fas fa-chevron-left"></i>
            </button>
        `;
        
        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= this.currentPage - 1 && i <= this.currentPage + 1)) {
                paginationHTML += `
                    <button class="${i === this.currentPage ? 'active' : ''}" 
                            onclick="shopManager.goToPage(${i})">
                        ${i}
                    </button>
                `;
            } else if (i === this.currentPage - 2 || i === this.currentPage + 2) {
                paginationHTML += '<span class="pagination-dots">...</span>';
            }
        }
        
        // Next button
        paginationHTML += `
            <button ${this.currentPage === totalPages ? 'disabled' : ''} 
                    onclick="shopManager.goToPage(${this.currentPage + 1})">
                <i class="fas fa-chevron-right"></i>
            </button>
        `;
        
        paginationContainer.innerHTML = paginationHTML;
    }
    
    goToPage(page) {
        this.currentPage = page;
        this.renderProducts();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    updateFilterCounts() {
        // Update category counts
        const categories = ['all', 'electronics', 'clothing', 'home', 'sports', 'books'];
        categories.forEach(category => {
            const countElement = document.getElementById(`${category}Count`);
            if (countElement) {
                const count = category === 'all' ? 
                    this.products.length : 
                    this.products.filter(p => p.category === category).length;
                countElement.textContent = count;
            }
        });
    }
    
    updateFilters() {
        this.updateFilterCounts();
    }
    
    // Cart Management
    addToCart(productId) {
        const product = this.products.find(p => p.id === productId);
        if (!product) return;
        
        const existingItem = this.cart.find(item => item.id === productId);
        
        if (existingItem) {
            existingItem.quantity += 1;
        } else {
            this.cart.push({ ...product, quantity: 1 });
        }
        
        this.updateCartUI();
        this.saveCartToStorage();
        this.showNotification('Item added to cart!', 'success');
    }
    
    removeFromCart(productId) {
        this.cart = this.cart.filter(item => item.id !== productId);
        this.updateCartUI();
        this.saveCartToStorage();
    }
    
    updateQuantity(productId, change) {
        const item = this.cart.find(item => item.id === productId);
        if (!item) return;
        
        item.quantity += change;
        
        if (item.quantity <= 0) {
            this.removeFromCart(productId);
        } else {
            this.updateCartUI();
            this.saveCartToStorage();
        }
    }
    
    updateCartUI() {
        const cartBadge = document.getElementById('cartBadge');
        const cartContent = document.getElementById('cartContent');
        const cartSubtotal = document.getElementById('cartSubtotal');
        const cartShipping = document.getElementById('cartShipping');
        const cartTotal = document.getElementById('cartTotal');
        
        // Update badge
        const totalItems = this.cart.reduce((sum, item) => sum + item.quantity, 0);
        if (cartBadge) {
            cartBadge.textContent = totalItems;
            cartBadge.style.display = totalItems > 0 ? 'flex' : 'none';
        }
        
        // Update cart content
        if (cartContent) {
            if (this.cart.length === 0) {
                cartContent.innerHTML = `
                    <div class="empty-cart">
                        <i class="fas fa-shopping-cart"></i>
                        <h4>Your cart is empty</h4>
                        <p>Start shopping to add items to your cart</p>
                    </div>
                `;
            } else {
                cartContent.innerHTML = this.cart.map(item => `
                    <div class="cart-item">
                        <div class="cart-item-image">${item.image}</div>
                        <div class="cart-item-info">
                            <div class="cart-item-name">${item.name}</div>
                            <div class="cart-item-price">$${item.price.toFixed(2)}</div>
                            <div class="quantity-controls">
                                <button class="quantity-btn" onclick="shopManager.updateQuantity(${item.id}, -1)">-</button>
                                <span class="quantity">${item.quantity}</span>
                                <button class="quantity-btn" onclick="shopManager.updateQuantity(${item.id}, 1)">+</button>
                            </div>
                        </div>
                        <button class="remove-item" onclick="shopManager.removeFromCart(${item.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                `).join('');
            }
        }
        
        // Update totals
        const subtotal = this.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        const shipping = subtotal >= 50 ? 0 : 9.99;
        const total = subtotal + shipping;
        
        if (cartSubtotal) cartSubtotal.textContent = `$${subtotal.toFixed(2)}`;
        if (cartShipping) cartShipping.textContent = shipping === 0 ? 'Free' : `$${shipping.toFixed(2)}`;
        if (cartTotal) cartTotal.textContent = `$${total.toFixed(2)}`;
    }
    
    // Storage
    saveCartToStorage() {
        localStorage.setItem('cart', JSON.stringify(this.cart));
    }
    
    loadCartFromStorage() {
        const savedCart = localStorage.getItem('cart');
        if (savedCart) {
            this.cart = JSON.parse(savedCart);
        }
    }
    
    // Search
    showSearchSuggestions(query) {
        const suggestionsContainer = document.getElementById('searchSuggestions');
        if (!suggestionsContainer || !query) {
            if (suggestionsContainer) suggestionsContainer.innerHTML = '';
            return;
        }
        
        const suggestions = this.products
            .filter(product => 
                product.name.toLowerCase().includes(query.toLowerCase()) ||
                product.tags.some(tag => tag.includes(query.toLowerCase()))
            )
            .slice(0, 5);
        
        if (suggestions.length > 0) {
            suggestionsContainer.innerHTML = suggestions.map(product => `
                <div class="search-suggestion" onclick="shopManager.selectSuggestion('${product.name}')">
                    <span class="suggestion-icon">${product.image}</span>
                    <span class="suggestion-name">${product.name}</span>
                    <span class="suggestion-price">$${product.price.toFixed(2)}</span>
                </div>
            `).join('');
        } else {
            suggestionsContainer.innerHTML = '<div class="no-suggestions">No products found</div>';
        }
    }
    
    selectSuggestion(productName) {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = productName;
            this.filters.search = productName.toLowerCase();
            this.applyFilters();
            this.hideSearch();
        }
    }
    
    hideSearch() {
        const searchOverlay = document.getElementById('searchOverlay');
        if (searchOverlay) {
            searchOverlay.style.display = 'none';
        }
    }
    
    // Quick View
    quickView(productId) {
        const product = this.products.find(p => p.id === productId);
        if (!product) return;
        
        const modal = document.getElementById('quickViewModal');
        const content = document.getElementById('quickViewContent');
        
        if (modal && content) {
            content.innerHTML = `
                <div class="quick-view-grid">
                    <div class="quick-view-image">
                        <div style="font-size: 120px; text-align: center; padding: 40px; background: var(--gray-50); border-radius: 12px;">
                            ${product.image}
                        </div>
                    </div>
                    <div class="quick-view-details">
                        <div class="product-category">${product.category}</div>
                        <h2>${product.name}</h2>
                        <div class="product-rating">
                            <div class="stars">${this.renderStars(product.rating)}</div>
                            <span class="rating-count">(${product.reviews} reviews)</span>
                        </div>
                        <p class="product-description">${product.description}</p>
                        <div class="product-price">
                            $${product.price.toFixed(2)}
                            ${product.originalPrice ? `<span class="original-price">$${product.originalPrice.toFixed(2)}</span>` : ''}
                        </div>
                        <div class="product-actions">
                            <button class="btn btn-primary" onclick="shopManager.addToCart(${product.id}); shopManager.closeQuickView();">
                                <i class="fas fa-shopping-cart"></i>
                                Add to Cart
                            </button>
                            <button class="btn btn-secondary" onclick="shopManager.toggleWishlist(${product.id})">
                                <i class="far fa-heart"></i>
                                Add to Wishlist
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            modal.style.display = 'flex';
        }
    }
    
    closeQuickView() {
        const modal = document.getElementById('quickViewModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    // Utility Methods
    toggleWishlist(productId) {
        this.showNotification('Wishlist feature coming soon!', 'info');
    }
    
    clearAllFilters() {
        // Reset all filters
        this.filters = {
            category: 'all',
            priceRange: 1000,
            brands: [],
            ratings: [],
            search: ''
        };
        
        // Reset UI
        document.querySelector('input[name="category"][value="all"]').checked = true;
        document.getElementById('priceRange').value = 1000;
        document.getElementById('priceValue').textContent = '1000';
        document.getElementById('minPrice').value = '';
        document.getElementById('maxPrice').value = '';
        document.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
        
        this.applyFilters();
    }
    
    showNotification(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check' : type === 'error' ? 'times' : 'info'}"></i>
            <span>${message}</span>
        `;
        
        notification.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            background: ${type === 'success' ? 'var(--success-color)' : type === 'error' ? 'var(--danger-color)' : 'var(--info-color)'};
            color: white;
            padding: 16px 20px;
            border-radius: 8px;
            box-shadow: var(--shadow-lg);
            z-index: 3000;
            display: flex;
            align-items: center;
            gap: 8px;
            transform: translateX(100%);
            transition: transform 0.3s ease;
            max-width: 300px;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    checkout() {
        if (this.cart.length === 0) {
            this.showNotification('Your cart is empty!', 'error');
            return;
        }
        
        const total = this.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        const itemCount = this.cart.reduce((sum, item) => sum + item.quantity, 0);
        
        // Simulate checkout process
        this.showNotification('Redirecting to checkout...', 'info');
        
        setTimeout(() => {
            alert(`Checkout Summary:\n\nItems: ${itemCount}\nTotal: $${total.toFixed(2)}\n\nThank you for your purchase!\n\nNote: This is a demo checkout.`);
            
            // Clear cart
            this.cart = [];
            this.updateCartUI();
            this.saveCartToStorage();
            toggleCart();
        }, 1000);
    }
}

// Global functions for HTML onclick handlers
function toggleSearch() {
    const searchOverlay = document.getElementById('searchOverlay');
    if (searchOverlay) {
        searchOverlay.style.display = searchOverlay.style.display === 'flex' ? 'none' : 'flex';
        if (searchOverlay.style.display === 'flex') {
            document.getElementById('searchInput').focus();
        }
    }
}

function toggleCart() {
    const cartSidebar = document.getElementById('cartSidebar');
    const overlay = document.getElementById('overlay');
    
    if (cartSidebar && overlay) {
        cartSidebar.classList.toggle('active');
        overlay.classList.toggle('active');
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('shopSidebar');
    const overlay = document.getElementById('overlay');
    
    if (sidebar && overlay) {
        sidebar.classList.toggle('active');
        overlay.classList.toggle('active');
    }
}

function clearAllFilters() {
    if (window.shopManager) {
        window.shopManager.clearAllFilters();
    }
}

function closeQuickView() {
    if (window.shopManager) {
        window.shopManager.closeQuickView();
    }
}

function checkout() {
    if (window.shopManager) {
        window.shopManager.checkout();
    }
}

// Initialize shop when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.shopManager = new ShopManager();
    
    // Close overlays when clicking outside
    document.getElementById('overlay').addEventListener('click', function() {
        toggleCart();
        toggleSidebar();
    });
    
    // Close search overlay when pressing Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const searchOverlay = document.getElementById('searchOverlay');
            const quickViewModal = document.getElementById('quickViewModal');
            
            if (searchOverlay && searchOverlay.style.display === 'flex') {
                toggleSearch();
            }
            
            if (quickViewModal && quickViewModal.style.display === 'flex') {
                closeQuickView();
            }
        }
    });
    
    // Mobile navigation toggle with body scroll lock
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            navMenu.classList.toggle('active');
            navToggle.classList.toggle('active');
            
            // Lock body scroll on mobile when menu is open
            if (window.innerWidth <= 768) {
                document.body.style.overflow = navMenu.classList.contains('active') ? 'hidden' : '';
            }
        });
        
        // Close mobile menu when clicking nav links
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    navMenu.classList.remove('active');
                    navToggle.classList.remove('active');
                    document.body.style.overflow = '';
                }
            });
        });
        
        // Close mobile menu on window resize
        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) {
                navMenu.classList.remove('active');
                navToggle.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    }
    
    // Mobile-specific optimizations
    if (window.innerWidth <= 768) {
        // Reduce animations on mobile for better performance
        document.documentElement.style.setProperty('--animation-duration', '0.2s');
        
        // Add touch feedback for product cards
        document.addEventListener('touchstart', function(e) {
            if (e.target.closest('.product-card')) {
                e.target.closest('.product-card').style.transform = 'scale(0.98)';
            }
        });
        
        document.addEventListener('touchend', function(e) {
            if (e.target.closest('.product-card')) {
                setTimeout(() => {
                    e.target.closest('.product-card').style.transform = '';
                }, 150);
            }
        });
    }
    
    // Handle orientation change
    window.addEventListener('orientationchange', function() {
        setTimeout(() => {
            // Recalculate viewport dimensions
            const vh = window.innerHeight * 0.01;
            document.documentElement.style.setProperty('--vh', `${vh}px`);
            
            // Close any open overlays on orientation change
            const searchOverlay = document.getElementById('searchOverlay');
            const cartSidebar = document.getElementById('cartSidebar');
            const shopSidebar = document.getElementById('shopSidebar');
            
            if (searchOverlay && searchOverlay.style.display === 'flex') {
                toggleSearch();
            }
            if (cartSidebar && cartSidebar.classList.contains('active')) {
                toggleCart();
            }
            if (shopSidebar && shopSidebar.classList.contains('active')) {
                toggleSidebar();
            }
        }, 100);
    });
    
    // Optimize scroll performance on mobile
    let ticking = false;
    function updateScrollPosition() {
        // Add any scroll-based animations here
        ticking = false;
    }
    
    window.addEventListener('scroll', function() {
        if (!ticking) {
            requestAnimationFrame(updateScrollPosition);
            ticking = true;
        }
    }, { passive: true });
});
