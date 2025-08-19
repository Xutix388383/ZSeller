
// Global variables
let cart = [];
let products = [];
let filteredProducts = [];

// Sample product data - replace with your actual product data
const sampleProducts = [
    {
        id: 1,
        name: "Professional Laptop",
        price: 899.99,
        category: "electronics",
        brand: "brand1",
        description: "High-performance laptop for professionals",
        image: "💻"
    },
    {
        id: 2,
        name: "Wireless Headphones",
        price: 199.99,
        category: "electronics",
        brand: "brand2",
        description: "Premium wireless headphones with noise cancellation",
        image: "🎧"
    },
    {
        id: 3,
        name: "Designer T-Shirt",
        price: 49.99,
        category: "clothing",
        brand: "brand3",
        description: "Comfortable cotton t-shirt with modern design",
        image: "👕"
    },
    {
        id: 4,
        name: "Smart Watch",
        price: 299.99,
        category: "electronics",
        brand: "brand1",
        description: "Feature-rich smartwatch with health monitoring",
        image: "⌚"
    },
    {
        id: 5,
        name: "Home Plant",
        price: 24.99,
        category: "home",
        brand: "brand2",
        description: "Beautiful indoor plant for home decoration",
        image: "🌱"
    },
    {
        id: 6,
        name: "Running Shoes",
        price: 129.99,
        category: "sports",
        brand: "brand3",
        description: "Comfortable running shoes for athletes",
        image: "👟"
    },
    {
        id: 7,
        name: "Programming Book",
        price: 39.99,
        category: "books",
        brand: "brand1",
        description: "Comprehensive guide to modern programming",
        image: "📚"
    },
    {
        id: 8,
        name: "Coffee Maker",
        price: 79.99,
        category: "home",
        brand: "brand2",
        description: "Automatic coffee maker for perfect morning brew",
        image: "☕"
    }
];

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    products = [...sampleProducts];
    filteredProducts = [...products];
    loadProducts();
    updateCartDisplay();
    initializePriceFilter();
    loadCartFromStorage();
});

// Sidebar functionality
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');
    
    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
}

// Cart functionality
function toggleCart() {
    const cartSidebar = document.getElementById('cartSidebar');
    const overlay = document.getElementById('overlay');
    
    cartSidebar.classList.toggle('active');
    overlay.classList.toggle('active');
}

// Search functionality
function toggleSearch() {
    const searchOverlay = document.getElementById('searchOverlay');
    const searchInput = document.getElementById('searchInput');
    
    if (searchOverlay.style.display === 'flex') {
        searchOverlay.style.display = 'none';
    } else {
        searchOverlay.style.display = 'flex';
        searchInput.focus();
    }
}

function searchProducts() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    filteredProducts = products.filter(product => 
        product.name.toLowerCase().includes(searchTerm) ||
        product.description.toLowerCase().includes(searchTerm) ||
        product.category.toLowerCase().includes(searchTerm)
    );
    loadProducts();
    toggleSearch();
}

// Filter functionality
function filterProducts(category) {
    if (category === 'all') {
        filteredProducts = [...products];
    } else {
        filteredProducts = products.filter(product => product.category === category);
    }
    loadProducts();
    toggleSidebar();
}

// Price filter
function initializePriceFilter() {
    const priceRange = document.getElementById('priceRange');
    const priceValue = document.getElementById('priceValue');
    
    priceRange.addEventListener('input', function() {
        const maxPrice = parseFloat(this.value);
        priceValue.textContent = maxPrice;
        
        filteredProducts = products.filter(product => product.price <= maxPrice);
        loadProducts();
    });
}

// Load and display products
function loadProducts() {
    const productsGrid = document.getElementById('productsGrid');
    
    if (filteredProducts.length === 0) {
        productsGrid.innerHTML = '<p style="text-align: center; color: #7f8c8d; grid-column: 1/-1;">No products found.</p>';
        return;
    }
    
    productsGrid.innerHTML = filteredProducts.map(product => `
        <div class="product-card" onclick="openProductModal(${product.id})">
            <div class="product-image">${product.image}</div>
            <div class="product-info">
                <h3 class="product-title">${product.name}</h3>
                <p class="product-description">${product.description}</p>
                <div class="product-footer">
                    <span class="product-price">$${product.price.toFixed(2)}</span>
                    <button class="add-to-cart" onclick="addToCart(${product.id}, event)">
                        Add to Cart
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// Cart management
function addToCart(productId, event) {
    event.stopPropagation();
    
    const product = products.find(p => p.id === productId);
    if (!product) return;
    
    const existingItem = cart.find(item => item.id === productId);
    
    if (existingItem) {
        existingItem.quantity += 1;
    } else {
        cart.push({
            ...product,
            quantity: 1
        });
    }
    
    updateCartDisplay();
    saveCartToStorage();
    showAddToCartFeedback();
}

function removeFromCart(productId) {
    cart = cart.filter(item => item.id !== productId);
    updateCartDisplay();
    saveCartToStorage();
}

function updateQuantity(productId, change) {
    const item = cart.find(item => item.id === productId);
    if (!item) return;
    
    item.quantity += change;
    
    if (item.quantity <= 0) {
        removeFromCart(productId);
    } else {
        updateCartDisplay();
        saveCartToStorage();
    }
}

function updateCartDisplay() {
    const cartContent = document.getElementById('cartContent');
    const cartCount = document.getElementById('cartCount');
    const cartTotal = document.getElementById('cartTotal');
    
    // Update cart count
    const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
    cartCount.textContent = totalItems;
    
    // Update cart total
    const total = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    cartTotal.textContent = total.toFixed(2);
    
    // Update cart content
    if (cart.length === 0) {
        cartContent.innerHTML = `
            <div class="empty-cart">
                <i class="fas fa-shopping-cart"></i>
                <p>Your cart is empty</p>
            </div>
        `;
    } else {
        cartContent.innerHTML = cart.map(item => `
            <div class="cart-item">
                <div class="cart-item-image">${item.image}</div>
                <div class="cart-item-info">
                    <h4>${item.name}</h4>
                    <div class="cart-item-price">$${item.price.toFixed(2)}</div>
                    <div class="quantity-controls">
                        <button onclick="updateQuantity(${item.id}, -1)">-</button>
                        <span>${item.quantity}</span>
                        <button onclick="updateQuantity(${item.id}, 1)">+</button>
                    </div>
                </div>
                <button class="remove-item" onclick="removeFromCart(${item.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `).join('');
    }
}

// Local storage for cart persistence
function saveCartToStorage() {
    localStorage.setItem('cart', JSON.stringify(cart));
}

function loadCartFromStorage() {
    const savedCart = localStorage.getItem('cart');
    if (savedCart) {
        cart = JSON.parse(savedCart);
        updateCartDisplay();
    }
}

// Product modal
function openProductModal(productId) {
    const product = products.find(p => p.id === productId);
    if (!product) return;
    
    const modal = document.getElementById('productModal');
    const modalBody = document.getElementById('modalBody');
    
    modalBody.innerHTML = `
        <div style="padding: 2rem;">
            <div style="display: flex; gap: 2rem; align-items: start;">
                <div style="font-size: 8rem; flex-shrink: 0;">${product.image}</div>
                <div style="flex: 1;">
                    <h2 style="color: #2c3e50; margin-bottom: 1rem;">${product.name}</h2>
                    <p style="color: #7f8c8d; margin-bottom: 1rem; line-height: 1.6;">${product.description}</p>
                    <div style="margin-bottom: 1rem;">
                        <span style="color: #95a5a6;">Category:</span>
                        <span style="color: #2c3e50; text-transform: capitalize;">${product.category}</span>
                    </div>
                    <div style="margin-bottom: 2rem;">
                        <span style="color: #95a5a6;">Brand:</span>
                        <span style="color: #2c3e50; text-transform: capitalize;">${product.brand}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 2rem; font-weight: 700; color: #27ae60;">$${product.price.toFixed(2)}</span>
                        <button onclick="addToCart(${product.id}); closeModal();" style="background: #3498db; color: white; border: none; padding: 1rem 2rem; border-radius: 5px; font-size: 1.1rem; cursor: pointer;">
                            Add to Cart
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    modal.style.display = 'block';
}

function closeModal() {
    const modal = document.getElementById('productModal');
    modal.style.display = 'none';
}

// Checkout functionality
function checkout() {
    if (cart.length === 0) {
        alert('Your cart is empty!');
        return;
    }
    
    const total = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const itemCount = cart.reduce((sum, item) => sum + item.quantity, 0);
    
    alert(`Checkout Summary:\n\nItems: ${itemCount}\nTotal: $${total.toFixed(2)}\n\nThank you for your purchase!\n\nNote: This is a demo. No actual payment was processed.`);
    
    // Clear cart after checkout
    cart = [];
    updateCartDisplay();
    saveCartToStorage();
    toggleCart();
}

// Contact form
function submitContactForm(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    
    // Simulate form submission
    alert('Thank you for your message! We will get back to you soon.');
    form.reset();
}

// Add to cart feedback
function showAddToCartFeedback() {
    // Create a temporary notification
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        background: #27ae60;
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 5px;
        z-index: 3000;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = 'Item added to cart!';
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 2000);
}

// Add slideIn animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);

// Close overlays when clicking outside
document.getElementById('overlay').addEventListener('click', function() {
    const sidebar = document.getElementById('sidebar');
    const cartSidebar = document.getElementById('cartSidebar');
    
    sidebar.classList.remove('active');
    cartSidebar.classList.remove('active');
    this.classList.remove('active');
});

// Close modal when clicking outside
window.addEventListener('click', function(event) {
    const modal = document.getElementById('productModal');
    if (event.target === modal) {
        closeModal();
    }
});

// Smooth scrolling for navigation
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Search on Enter key
document.getElementById('searchInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        searchProducts();
    }
});
