import axios from 'axios';

// API Configuration - Use /api/ prefix to go through nginx proxy
const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

// Create axios instance with default config
const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor to add auth token
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('authToken');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor for error handling
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Token expired or invalid
            localStorage.removeItem('authToken');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

// Export the api instance
export { api };

// Authentication API
export const authAPI = {
    // Register new user
    register: async (userData) => {
        const response = await api.post('/auth/register', userData);
        return response.data;
    },

    // Login user
    login: async (credentials) => {
        const response = await api.post('/auth/login', credentials);
        return response.data;
    },

    // Logout (client-side)
    logout: () => {
        localStorage.removeItem('authToken');
        localStorage.removeItem('user');
    },

    // Check if user is authenticated
    isAuthenticated: () => {
        return !!localStorage.getItem('authToken');
    },

    // Get current user info
    getCurrentUser: () => {
        const user = localStorage.getItem('user');
        return user ? JSON.parse(user) : null;
    }
};

// Products API
export const productsAPI = {
    // Search products
    search: async (params = {}) => {
        const response = await api.get('/products/search', { params });
        return response.data;
    },

    // Get product details
    getProduct: async (productId) => {
        const response = await api.get(`/products/${productId}`);
        return response.data;
    },

    // Get product price history
    getPriceHistory: async (productId, days = 30, vendor = null) => {
        const params = { days, ...(vendor && { vendor }) };
        const response = await api.get(`/products/${productId}/history`, { params });
        return response.data;
    },

    // Add new product (custom endpoint - would need to be implemented in backend)
    addProduct: async (productData) => {
        const response = await api.post('/products/add', productData);
        return response.data;
    },

    // Update product (custom endpoint - would need to be implemented in backend)
    updateProduct: async (productId, productData) => {
        const response = await api.put(`/products/${productId}`, productData);
        return response.data;
    },

    // Delete product (custom endpoint - would need to be implemented in backend)
    deleteProduct: async (productId) => {
        const response = await api.delete(`/products/${productId}`);
        return response.data;
    },

    // Refresh product prices (custom endpoint - would need to be implemented in backend)
    refreshPrices: async (productId) => {
        const response = await api.post(`/products/${productId}/refresh-prices`);
        return response.data;
    }
};

// Alerts API
export const alertsAPI = {
    // Create price alert
    createAlert: async (alertData) => {
        const response = await api.post('/alerts/create', alertData);
        return response.data;
    },

    // Get user alerts (custom endpoint - would need to be implemented in backend)
    getUserAlerts: async () => {
        const response = await api.get('/alerts/user');
        return response.data;
    },

    // Delete alert (custom endpoint - would need to be implemented in backend)
    deleteAlert: async (alertId) => {
        const response = await api.delete(`/alerts/${alertId}`);
        return response.data;
    }
};

// Market Trends API
export const marketAPI = {
    // Get market trends
    getTrends: async (category = null) => {
        const params = category ? { category } : {};
        const response = await api.get('/market/trends', { params });
        return response.data;
    },

    // Get exchange rates
    getExchangeRates: async () => {
        const response = await api.get('/exchange-rates/current');
        return response.data;
    }
};

// Website Monitoring API (custom endpoints - would need to be implemented in backend)
export const websiteAPI = {
    // Get monitored websites
    getWebsites: async () => {
        const response = await api.get('/websites');
        return response.data;
    },

    // Add new website
    addWebsite: async (websiteData) => {
        const response = await api.post('/websites', websiteData);
        return response.data;
    },

    // Update website
    updateWebsite: async (websiteId, websiteData) => {
        const response = await api.put(`/websites/${websiteId}`, websiteData);
        return response.data;
    },

    // Delete website
    deleteWebsite: async (websiteId) => {
        const response = await api.delete(`/websites/${websiteId}`);
        return response.data;
    },

    // Manual scrape website
    manualScrape: async (websiteId) => {
        const response = await api.post(`/websites/${websiteId}/scrape`);
        return response.data;
    },

    // Get website statistics
    getWebsiteStats: async (websiteId) => {
        const response = await api.get(`/websites/${websiteId}/stats`);
        return response.data;
    }
};

// Health and Monitoring API
export const healthAPI = {
    // Get API health status
    getHealth: async () => {
        const response = await api.get('/health');
        return response.data;
    },

    // Get API metrics
    getMetrics: async () => {
        const response = await api.get('/metrics');
        return response.data;
    }
};

// Mock data for development (when backend endpoints are not available)
export const mockData = {
    products: [
        {
            product_id: 'PROD001',
            canonical_title: 'Samsung Galaxy S21',
            canonical_title_fa: 'سامسونگ گلکسی اس ۲۱',
            brand: 'Samsung',
            category: 'mobile',
            current_prices: [
                {
                    vendor: 'digikala.com',
                    vendor_name_fa: 'دیجی‌کالا',
                    price_toman: 25000000,
                    price_usd: 588,
                    availability: true,
                    product_url: 'https://digikala.com/product/samsung-galaxy-s21'
                },
                {
                    vendor: 'technolife.ir',
                    vendor_name_fa: 'تکنولایف',
                    price_toman: 24500000,
                    price_usd: 576,
                    availability: true,
                    product_url: 'https://technolife.ir/product/samsung-galaxy-s21'
                }
            ],
            lowest_price: {
                vendor: 'technolife.ir',
                vendor_name_fa: 'تکنولایف',
                price_toman: 24500000,
                price_usd: 576
            },
            highest_price: {
                vendor: 'digikala.com',
                vendor_name_fa: 'دیجی‌کالا',
                price_toman: 25000000,
                price_usd: 588
            },
            price_range_pct: 2.0,
            available_vendors: 2,
            last_updated: new Date().toISOString()
        },
        {
            product_id: 'PROD002',
            canonical_title: 'iPhone 13 Pro',
            canonical_title_fa: 'آیفون ۱۳ پرو',
            brand: 'Apple',
            category: 'mobile',
            current_prices: [
                {
                    vendor: 'snap.ir',
                    vendor_name_fa: 'اسنپ',
                    price_toman: 32500000,
                    price_usd: 765,
                    availability: true,
                    product_url: 'https://snap.ir/product/iphone-13-pro'
                }
            ],
            lowest_price: {
                vendor: 'snap.ir',
                vendor_name_fa: 'اسنپ',
                price_toman: 32500000,
                price_usd: 765
            },
            highest_price: {
                vendor: 'snap.ir',
                vendor_name_fa: 'اسنپ',
                price_toman: 32500000,
                price_usd: 765
            },
            price_range_pct: 0,
            available_vendors: 1,
            last_updated: new Date().toISOString()
        }
    ],
    websites: [
        {
            id: 'WEB001',
            name: 'Digikala',
            url: 'https://www.digikala.com',
            status: 'active',
            lastScraped: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
            productsFound: 15420,
            priceChanges: 342,
            successRate: 98.5,
            nextScrape: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
            categories: ['mobile', 'laptop', 'tablet', 'accessories']
        },
        {
            id: 'WEB002',
            name: 'DigiKala',
            url: 'https://digikala.com',
            status: 'active',
            lastScraped: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
            productsFound: 8920,
            priceChanges: 156,
            successRate: 95.2,
            nextScrape: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
            categories: ['mobile', 'laptop']
        },
        {
            id: 'WEB003',
            name: 'MeghdadIT',
            url: 'https://www.meghdadit.com',
            status: 'active',
            lastScraped: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
            productsFound: 5670,
            priceChanges: 89,
            successRate: 99.1,
            nextScrape: new Date(Date.now() + 45 * 60 * 1000).toISOString(),
            categories: ['mobile', 'accessories']
        }
    ]
};

// Utility function to check if API is available
export const checkAPIHealth = async () => {
    try {
        const response = await api.get('/health');

        // Check if API returned proper health data
        const isHealthy = response.status === 200 &&
            response.data &&
            response.data.status === 'healthy';

        if (isHealthy) {
            console.log('API health check successful, services:', response.data.services);
            return true;
        } else {
            console.warn('API health check failed - unhealthy status or invalid response');
            return false;
        }
    } catch (error) {
        console.warn('API not available, using mock data:', error.message);
        return false;
    }
};

export default api;
