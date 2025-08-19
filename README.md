
# Professional E-commerce Template

A modern, responsive e-commerce website template with full shopping cart functionality, sidebar navigation, and professional styling.

## Features

### 🛒 Complete Shopping Cart System
- Add/remove items from cart
- Quantity management
- Real-time total calculation
- Cart persistence with localStorage
- Smooth checkout process

### 🎨 Professional Design
- Modern, clean interface
- Responsive design for all devices
- Smooth animations and transitions
- Professional color scheme
- Font Awesome icons

### 📱 Mobile-First Responsive
- Fully responsive sidebar and cart
- Optimized for mobile, tablet, and desktop
- Touch-friendly interface
- Adaptive layouts

### 🔍 Advanced Features
- Product search functionality
- Category filtering
- Price range filtering
- Brand filtering
- Product modal with detailed view

### 📋 Ready-to-Use Sections
- Hero section with call-to-action
- Featured products grid
- About section with features
- Contact form
- Professional footer

## Quick Start

1. **Clone or download** this template
2. **Customize the content**:
   - Update `index.html` with your business information
   - Modify `script.js` to add your products
   - Adjust colors and styling in `style.css`
3. **Run the server**:
   ```bash
   python server.py
   ```
4. **Open your browser** and navigate to the displayed URL

## Customization Guide

### Adding Products

Edit the `sampleProducts` array in `script.js`:

```javascript
const sampleProducts = [
    {
        id: 1,
        name: "Your Product Name",
        price: 99.99,
        category: "electronics", // electronics, clothing, home, sports, books
        brand: "brand1", // brand1, brand2, brand3
        description: "Product description here",
        image: "🔥" // Use emoji or replace with actual image URLs
    }
    // Add more products...
];
```

### Customizing Colors

Main color variables in `style.css`:
- Primary: `#3498db` (blue)
- Success: `#27ae60` (green)
- Warning: `#f39c12` (orange)
- Danger: `#e74c3c` (red)
- Dark: `#2c3e50`
- Light: `#ecf0f1`

### Updating Business Information

1. **Header**: Change logo and company name in `index.html`
2. **Hero Section**: Update welcome message and call-to-action
3. **About Section**: Replace with your business information
4. **Contact Section**: Update contact details and form
5. **Footer**: Customize footer links and information

### Categories and Filters

Update categories in the sidebar by modifying:
- Category list in `index.html`
- Filter functions in `script.js`
- Add corresponding products with matching category names

## File Structure

```
├── index.html          # Main HTML structure
├── style.css           # All styling and responsive design
├── script.js           # Cart system and functionality
├── server.py           # Python development server
├── .replit             # Replit configuration
└── README.md           # This file
```

## Browser Support

- ✅ Chrome (recommended)
- ✅ Firefox
- ✅ Safari
- ✅ Edge
- ✅ Mobile browsers

## Development Server

The included `server.py` automatically finds an available port and serves your files:

```bash
python server.py
```

Features:
- Automatic port detection (5000-5099)
- CORS enabled for development
- Serves static files
- Clean shutdown on Ctrl+C

## Deployment

This template is ready for deployment on any static hosting platform:

1. **Replit**: Already configured - just click "Deploy"
2. **Netlify**: Drag and drop the files
3. **Vercel**: Connect your repository
4. **GitHub Pages**: Push to a repository

## License

This template is free to use for personal and commercial projects. No attribution required, but appreciated!

## Support

For questions or customization help:
- Check the code comments in each file
- Review the examples in `script.js`
- Modify the sample data to match your needs

---

**Happy selling!** 🚀
