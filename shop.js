
// Enhanced Shop Functionality for STK Supply
class ShopManager {
    constructor() {
        this.products = [];
        this.filteredProducts = [];
        this.cart = [];
        this.currentPage = 1;
        this.itemsPerPage = 12;
        this.filters = {
            category: 'weapons',
            subcategory: 'all',
            priceRange: 1000,
            brands: [],
            ratings: [],
            search: ''
        };
        this.selectedWeapon = null;
        this.sortBy = 'featured';
        this.viewMode = 'grid';
        
        this.init();
    }
    
    init() {
        this.loadProducts();
        this.loadCartFromStorage();
        this.bindEvents();
        this.renderProducts();
        this.updateCartUI();
        this.handleURLParams();
    }
    
    loadProducts() {
        // Weapon List - All weapons are free
        this.weapons = [
            "GoldenButton", "GreenSwitch", "BlueTips/Switch", "OrangeButton", "BinaryTrigger",
            "YellowButtonSwitch", "FullyARP", "FullyDraco", "Fully-MicroAR", "Cyanbutton",
            "100RndTanG19", "300ARG", "VP9Scope", "MasterPiece30", "GSwitch",
            "G17WittaButton", "G19Switch", "G20Switch", "G21Switch", "G22 Switch",
            "G23 Switch", "G40 Switch", "G42 Switch", "Fully-FN", "BinaryARP",
            "BinaryDraco", "CustomAR9"
        ];

        // STK Supply Product Catalog
        this.products = [
            // Package Options for Weapons
            { id: 1, name: "Safe Package", price: 3.00, category: "weapons", subcategory: "safe", description: "Premium safe storage for your weapon", image: "🔒", rating: 4.9, reviews: 1234, inStock: true, featured: true },
            { id: 2, name: "Bag Package", price: 2.00, category: "weapons", subcategory: "bag", description: "Premium bag storage for your weapon", image: "🎒", rating: 4.8, reviews: 987, inStock: true, featured: true },
            { id: 3, name: "Trunk Package", price: 1.00, category: "weapons", subcategory: "trunk", description: "Basic trunk storage for your weapon", image: "📦", rating: 4.7, reviews: 756, inStock: true, featured: true },

            // Money - Regular ($1 each)
            { id: 49, name: "Max Money 990k", price: 1.00, category: "money", subcategory: "regular", description: "Clean money package • Regular option", image: "💰", rating: 4.9, reviews: 567, inStock: true, featured: true },
            { id: 50, name: "Max Bank 990k", price: 1.00, category: "money", subcategory: "regular", description: "Max out your bank • Regular option", image: "🏦", rating: 4.8, reviews: 432, inStock: true, featured: true },

            // Money - Gamepass ($2 each)
            { id: 51, name: "Max Money 1.6M (Extra Money Pass)", price: 2.00, category: "money", subcategory: "gamepass", description: "Extra Money Pass exclusive • Higher limits", image: "💎", rating: 4.9, reviews: 321, inStock: true, featured: true },
            { id: 52, name: "Max Bank 1.6M (Extra Bank Pass)", price: 2.00, category: "money", subcategory: "gamepass", description: "Extra Bank Pass exclusive • Higher limits", image: "💳", rating: 4.8, reviews: 289, inStock: true, featured: true },

            // Watches ($1 each)
            { id: 53, name: "Cartier", price: 1.00, category: "watches", subcategory: "luxury", description: "Luxury Cartier watch", image: "⌚", rating: 4.9, reviews: 178, inStock: true, featured: true },
            { id: 54, name: "BlueFaceCartier", price: 1.00, category: "watches", subcategory: "luxury", description: "Blue Face Cartier watch", image: "⌚", rating: 4.8, reviews: 156, inStock: true, featured: true },
            { id: 55, name: "White Richard Millie", price: 1.00, category: "watches", subcategory: "luxury", description: "White Richard Mille watch", image: "⌚", rating: 4.9, reviews: 234, inStock: true, featured: true },
            { id: 56, name: "PinkRichard", price: 1.00, category: "watches", subcategory: "luxury", description: "Pink Richard Mille watch", image: "⌚", rating: 4.8, reviews: 189, inStock: true, featured: true },
            { id: 57, name: "GreenRichard", price: 1.00, category: "watches", subcategory: "luxury", description: "Green Richard Mille watch", image: "⌚", rating: 4.7, reviews: 167, inStock: true, featured: false },
            { id: 58, name: "RedRichard", price: 1.00, category: "watches", subcategory: "luxury", description: "Red Richard Mille watch", image: "⌚", rating: 4.8, reviews: 145, inStock: true, featured: true },
            { id: 59, name: "BluRichard", price: 1.00, category: "watches", subcategory: "luxury", description: "Blue Richard Mille watch", image: "⌚", rating: 4.9, reviews: 198, inStock: true, featured: true },
            { id: 60, name: "BlackOutMillie", price: 1.00, category: "watches", subcategory: "luxury", description: "BlackOut Mille watch", image: "⌚", rating: 4.8, reviews: 176, inStock: true, featured: true },
            { id: 61, name: "Red AP", price: 1.00, category: "watches", subcategory: "luxury", description: "Red Audemars Piguet", image: "⌚", rating: 4.7, reviews: 134, inStock: true, featured: false },
            { id: 62, name: "AP Watch", price: 1.00, category: "watches", subcategory: "luxury", description: "Classic Audemars Piguet", image: "⌚", rating: 4.9, reviews: 210, inStock: true, featured: true },
            { id: 63, name: "Gold AP", price: 1.00, category: "watches", subcategory: "luxury", description: "Gold Audemars Piguet", image: "⌚", rating: 4.8, reviews: 187, inStock: true, featured: true },
            { id: 64, name: "Red AP Watch", price: 1.00, category: "watches", subcategory: "luxury", description: "Red AP Watch variant", image: "⌚", rating: 4.7, reviews: 156, inStock: true, featured: false },
            { id: 65, name: "CubanG AP", price: 1.00, category: "watches", subcategory: "luxury", description: "Cuban Gold AP", image: "⌚", rating: 4.8, reviews: 178, inStock: true, featured: true },
            { id: 66, name: "CubanP AP", price: 1.00, category: "watches", subcategory: "luxury", description: "Cuban Pink AP", image: "⌚", rating: 4.7, reviews: 145, inStock: true, featured: false },
            { id: 67, name: "CubanB AP", price: 1.00, category: "watches", subcategory: "luxury", description: "Cuban Blue AP", image: "⌚", rating: 4.8, reviews: 167, inStock: true, featured: true },
            { id: 68, name: "Iced AP", price: 1.00, category: "watches", subcategory: "luxury", description: "Iced out Audemars Piguet", image: "⌚", rating: 4.9, reviews: 234, inStock: true, featured: true }
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
                this.filters.subcategory = 'all'; // Reset subcategory when changing main category
                this.applyFilters();
                this.renderSubcategoryTabs();
            });
        });

        // Subcategory tabs
        this.bindSubcategoryEvents();
        
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

        // Initialize with weapons category
        this.renderSubcategoryTabs();
    }

    bindSubcategoryEvents() {
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('subcategory-tab')) {
                const subcategory = e.target.dataset.subcategory;
                
                // Update active tab
                document.querySelectorAll('.subcategory-tab').forEach(t => t.classList.remove('active'));
                e.target.classList.add('active');
                
                // Update filter
                this.filters.subcategory = subcategory;
                this.applyFilters();
            }
            
            if (e.target.classList.contains('weapon-tab')) {
                const weapon = e.target.dataset.weapon;
                
                // Update active tab
                document.querySelectorAll('.weapon-tab').forEach(t => t.classList.remove('active'));
                e.target.classList.add('active');
                
                // Update selected weapon
                this.selectedWeapon = weapon;
                this.applyFilters();
            }
        });
    }

    renderSubcategoryTabs() {
        const subcategoryContainer = document.querySelector('.subcategory-tabs');
        if (!subcategoryContainer) {
            // Create subcategory container after category tabs
            const categorySection = document.querySelector('.filter-section');
            const subcategorySection = document.createElement('div');
            subcategorySection.className = 'filter-section';
            subcategorySection.innerHTML = `
                <h4>Weapon Selection</h4>
                <div class="weapon-tabs"></div>
                <h4 style="margin-top: 24px;">Package Type</h4>
                <div class="subcategory-tabs"></div>
            `;
            categorySection.parentNode.insertBefore(subcategorySection, categorySection.nextSibling);
        }

        const weaponContainer = document.querySelector('.weapon-tabs');
        const container = document.querySelector('.subcategory-tabs');
        if (!container) return;

        if (this.filters.category === 'weapons') {
            // Render weapon selection tabs
            if (weaponContainer) {
                weaponContainer.innerHTML = this.weapons.map(weapon => `
                    <button class="weapon-tab ${this.selectedWeapon === weapon ? 'active' : ''}" 
                            data-weapon="${weapon}">
                        <i>🔫</i>
                        <span>${weapon}</span>
                    </button>
                `).join('');
            }

            // Render package type tabs
            const subcategories = [
                { id: 'safe', name: 'Safe ($3)', icon: '🔒' },
                { id: 'bag', name: 'Bag ($2)', icon: '🎒' },
                { id: 'trunk', name: 'Trunk ($1)', icon: '📦' }
            ];

            container.innerHTML = subcategories.map(sub => `
                <button class="subcategory-tab ${this.filters.subcategory === sub.id ? 'active' : ''}" 
                        data-subcategory="${sub.id}">
                    <i>${sub.icon}</i>
                    <span>${sub.name}</span>
                </button>
            `).join('');
        } else if (this.filters.category === 'money') {
            // Hide weapon tabs for money category
            if (weaponContainer) weaponContainer.innerHTML = '';
            
            const subcategories = [
                { id: 'all', name: 'All Options', icon: '💰' },
                { id: 'regular', name: 'Regular ($1)', icon: '💵' },
                { id: 'gamepass', name: 'Gamepass ($2)', icon: '💎' }
            ];

            container.innerHTML = subcategories.map(sub => `
                <button class="subcategory-tab ${this.filters.subcategory === sub.id ? 'active' : ''}" 
                        data-subcategory="${sub.id}">
                    <i>${sub.icon}</i>
                    <span>${sub.name}</span>
                </button>
            `).join('');
        } else if (this.filters.category === 'watches') {
            // Hide weapon tabs for watches category
            if (weaponContainer) weaponContainer.innerHTML = '';
            
            const subcategories = [
                { id: 'all', name: 'All Watches', icon: '⌚' },
                { id: 'luxury', name: 'Luxury ($1)', icon: '💎' }
            ];

            container.innerHTML = subcategories.map(sub => `
                <button class="subcategory-tab ${this.filters.subcategory === sub.id ? 'active' : ''}" 
                        data-subcategory="${sub.id}">
                    <i>${sub.icon}</i>
                    <span>${sub.name}</span>
                </button>
            `).join('');
        }
    }
    
    handleURLParams() {
        const urlParams = new URLSearchParams(window.location.search);
        const category = urlParams.get('category');
        
        if (category && ['weapons', 'money', 'watches'].includes(category)) {
            this.filters.category = category;
            const categoryTab = document.querySelector(`[data-category="${category}"]`);
            if (categoryTab) {
                document.querySelectorAll('.category-tab').forEach(t => t.classList.remove('active'));
                categoryTab.classList.add('active');
            }
            this.renderSubcategoryTabs();
            this.applyFilters();
        }
    }
    
    applyFilters() {
        this.filteredProducts = this.products.filter(product => {
            // Category filter
            if (this.filters.category && product.category !== this.filters.category) {
                return false;
            }
            
            // Subcategory filter
            if (this.filters.subcategory && this.filters.subcategory !== 'all' && product.subcategory !== this.filters.subcategory) {
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
            
            // Search filter
            if (this.filters.search) {
                const searchTerm = this.filters.search.toLowerCase();
                return product.name.toLowerCase().includes(searchTerm) ||
                       product.description.toLowerCase().includes(searchTerm);
            }
            
            return true;
        });
        
        this.currentPage = 1;
        this.sortProducts();
        this.renderProducts();
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
        }, 100);
    }
    
    createProductCard(product) {
        if (this.filters.category === 'weapons') {
            const weaponName = this.selectedWeapon || 'Select a weapon';
            const isDisabled = !this.selectedWeapon;
            
            return `
                <div class="product-card ${isDisabled ? 'disabled' : ''}" data-product-id="${product.id}">
                    <div class="product-image">
                        ${product.image}
                        <div class="product-actions">
                            <button class="action-btn" onclick="shopManager.quickView(${product.id})" title="Quick View">
                                <i class="fas fa-eye"></i>
                            </button>
                        </div>
                    </div>
                    <div class="product-info">
                        <div class="product-category">Weapon Package</div>
                        <h3 class="product-title">${weaponName} + ${product.name}</h3>
                        <div class="package-details">
                            <div class="weapon-info">🔫 ${weaponName} (FREE)</div>
                            <div class="package-info">${product.image} ${product.name}</div>
                        </div>
                        <div class="product-rating">
                            <div class="stars">
                                ${this.renderStars(product.rating)}
                            </div>
                            <span class="rating-count">(${product.reviews})</span>
                        </div>
                        <div class="product-price">
                            $${product.price.toFixed(2)}
                            <small>Package only</small>
                        </div>
                        ${product.inStock && !isDisabled ? 
                            `<button class="add-to-cart" onclick="shopManager.addToCart(${product.id})">
                                <i class="fas fa-shopping-cart"></i>
                                Add to Cart
                            </button>` :
                            `<button class="add-to-cart coming-soon" disabled>
                                <i class="fas fa-${isDisabled ? 'exclamation-triangle' : 'clock'}"></i>
                                ${isDisabled ? 'Select Weapon First' : 'Coming Soon'}
                            </button>`
                        }
                    </div>
                </div>
            `;
        }
        
        return `
            <div class="product-card" data-product-id="${product.id}">
                <div class="product-image">
                    ${product.image}
                    <div class="product-actions">
                        <button class="action-btn" onclick="shopManager.quickView(${product.id})" title="Quick View">
                            <i class="fas fa-eye"></i>
                        </button>
                    </div>
                </div>
                <div class="product-info">
                    <div class="product-category">${product.category} • ${product.subcategory}</div>
                    <h3 class="product-title">${product.name}</h3>
                    <div class="product-rating">
                        <div class="stars">
                            ${this.renderStars(product.rating)}
                        </div>
                        <span class="rating-count">(${product.reviews})</span>
                    </div>
                    <div class="product-price">
                        $${product.price.toFixed(2)}
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
    
    // Cart Management
    addToCart(productId) {
        const product = this.products.find(p => p.id === productId);
        if (!product) return;
        
        // For weapons, require weapon selection
        if (this.filters.category === 'weapons' && !this.selectedWeapon) {
            this.showNotification('Please select a weapon first!', 'error');
            return;
        }
        
        let cartItem = { ...product, quantity: 1 };
        
        // Add weapon info for weapon packages
        if (this.filters.category === 'weapons' && this.selectedWeapon) {
            cartItem.weaponName = this.selectedWeapon;
            cartItem.name = `${this.selectedWeapon} + ${product.name}`;
            cartItem.uniqueId = `${productId}-${this.selectedWeapon}`;
        }
        
        const uniqueId = cartItem.uniqueId || productId;
        const existingItem = this.cart.find(item => (item.uniqueId || item.id) === uniqueId);
        
        if (existingItem) {
            existingItem.quantity += 1;
        } else {
            this.cart.push(cartItem);
        }
        
        this.updateCartUI();
        this.saveCartToStorage();
        this.showNotification('Item added to cart!', 'success');
    }
    
    removeFromCart(uniqueId) {
        this.cart = this.cart.filter(item => (item.uniqueId || item.id) !== uniqueId);
        this.updateCartUI();
        this.saveCartToStorage();
    }
    
    updateQuantity(uniqueId, change) {
        const item = this.cart.find(item => (item.uniqueId || item.id) === uniqueId);
        if (!item) return;
        
        item.quantity += change;
        
        if (item.quantity <= 0) {
            this.removeFromCart(uniqueId);
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
                cartContent.innerHTML = this.cart.map(item => {
                    const uniqueId = item.uniqueId || item.id;
                    return `
                        <div class="cart-item">
                            <div class="cart-item-image">${item.image}</div>
                            <div class="cart-item-info">
                                <div class="cart-item-name">${item.name}</div>
                                ${item.weaponName ? `<div class="cart-item-weapon">🔫 ${item.weaponName} (Free)</div>` : ''}
                                <div class="cart-item-price">$${item.price.toFixed(2)}</div>
                                <div class="quantity-controls">
                                    <button class="quantity-btn" onclick="shopManager.updateQuantity('${uniqueId}', -1)">-</button>
                                    <span class="quantity">${item.quantity}</span>
                                    <button class="quantity-btn" onclick="shopManager.updateQuantity('${uniqueId}', 1)">+</button>
                                </div>
                            </div>
                            <button class="remove-item" onclick="shopManager.removeFromCart('${uniqueId}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    `;
                }).join('');
            }
        }
        
        // Update totals
        const subtotal = this.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        const shipping = 0; // Free shipping for digital products
        const total = subtotal + shipping;
        
        if (cartSubtotal) cartSubtotal.textContent = `$${subtotal.toFixed(2)}`;
        if (cartShipping) cartShipping.textContent = 'Free';
        if (cartTotal) cartTotal.textContent = `$${total.toFixed(2)}`;
    }
    
    // Storage
    saveCartToStorage() {
        localStorage.setItem('stkCart', JSON.stringify(this.cart));
    }
    
    loadCartFromStorage() {
        const savedCart = localStorage.getItem('stkCart');
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
                product.description.toLowerCase().includes(query.toLowerCase())
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
                        <div class="product-category">${product.category} • ${product.subcategory}</div>
                        <h2>${product.name}</h2>
                        <div class="product-rating">
                            <div class="stars">${this.renderStars(product.rating)}</div>
                            <span class="rating-count">(${product.reviews} reviews)</span>
                        </div>
                        <p class="product-description">${product.description}</p>
                        <div class="product-price">
                            $${product.price.toFixed(2)}
                        </div>
                        <div class="product-actions" style="margin-top: 24px;">
                            <button class="btn btn-primary" onclick="shopManager.addToCart(${product.id}); shopManager.closeQuickView();" style="width: 100%; margin-bottom: 12px;">
                                <i class="fas fa-shopping-cart"></i>
                                Add to Cart - $${product.price.toFixed(2)}
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
    clearAllFilters() {
        // Reset all filters
        this.filters = {
            category: 'weapons',
            subcategory: 'all',
            priceRange: 1000,
            brands: [],
            ratings: [],
            search: ''
        };
        
        // Reset UI
        document.querySelector('[data-category="weapons"]').click();
        document.getElementById('priceRange').value = 1000;
        document.getElementById('priceValue').textContent = '1000';
        document.getElementById('minPrice').value = '';
        document.getElementById('maxPrice').value = '';
        document.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
        
        this.renderSubcategoryTabs();
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
        
        // Show order summary
        const orderSummary = this.cart.map(item => 
            `${item.quantity}x ${item.name} - $${(item.price * item.quantity).toFixed(2)}`
        ).join('\n');
        
        alert(`STK Supply Order Summary:\n\n${orderSummary}\n\nTotal Items: ${itemCount}\nTotal: $${total.toFixed(2)}\n\nThank you for your order!\n\nNote: This is a demo. Contact STK Supply for actual orders.`);
        
        // Clear cart
        this.cart = [];
        this.updateCartUI();
        this.saveCartToStorage();
        toggleCart();
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
    
    // Mobile navigation toggle
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            navMenu.classList.toggle('active');
            navToggle.classList.toggle('active');
            
            if (window.innerWidth <= 768) {
                document.body.style.overflow = navMenu.classList.contains('active') ? 'hidden' : '';
            }
        });
        
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    navMenu.classList.remove('active');
                    navToggle.classList.remove('active');
                    document.body.style.overflow = '';
                }
            });
        });
        
        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) {
                navMenu.classList.remove('active');
                navToggle.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    }
});
