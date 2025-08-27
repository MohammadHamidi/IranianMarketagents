import React, { useState, useEffect } from 'react';
import {
    Card,
    Table,
    Input,
    Button,
    Space,
    Tag,
    Modal,
    Form,
    Select,
    message,
    Popconfirm,
    Tooltip,
    Row,
    Col,
    Statistic,
    Divider,
    Alert
} from 'antd';
import {
    SearchOutlined,
    PlusOutlined,
    EditOutlined,
    DeleteOutlined,
    EyeOutlined,
    LinkOutlined,
    ReloadOutlined,
    DollarOutlined,
    ShoppingOutlined
} from '@ant-design/icons';
import { api, productsAPI, checkAPIHealth, mockData } from '../services/api';

const { Option } = Select;

const Products = () => {
    const [products, setProducts] = useState([]);
    const [loading, setLoading] = useState(false);
    const [searchText, setSearchText] = useState('');
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [editingProduct, setEditingProduct] = useState(null);
    const [form] = Form.useForm();
    const [stats, setStats] = useState({
        totalProducts: 0,
        activeProducts: 0,
        totalValue: 0
    });
    const [apiAvailable, setApiAvailable] = useState(false);
    const [dataStatus, setDataStatus] = useState({ real_data_flag: false });

    // AI Discovery states
    const [aiDiscoveryVisible, setAiDiscoveryVisible] = useState(false);
    const [aiDiscoveryLoading, setAiDiscoveryLoading] = useState(false);
    const [discoveredWebsites, setDiscoveredWebsites] = useState([]);
    const [websiteSuggestions, setWebsiteSuggestions] = useState([]);

    // Product details modal state
    const [detailsModalVisible, setDetailsModalVisible] = useState(false);
    const [selectedProduct, setSelectedProduct] = useState(null);

    // AI Discovery functions
    const handleAiDiscovery = async () => {
        setAiDiscoveryLoading(true);
        try {
            const response = await api.post('/ai/discover-websites');
            setDiscoveredWebsites(response.data.candidates || []);
            setAiDiscoveryVisible(true);
            message.success(`AI discovered ${response.data.candidates?.length || 0} potential websites!`);
        } catch (error) {
            message.error('AI discovery failed: ' + (error.response?.data?.detail || error.message));
        } finally {
            setAiDiscoveryLoading(false);
        }
    };

    const loadWebsiteSuggestions = async () => {
        try {
            const response = await api.get('/ai/website-suggestions');
            setWebsiteSuggestions(response.data.suggestions || []);
        } catch (error) {
            console.error('Failed to load website suggestions:', error);
        }
    };

    const addDiscoveredWebsite = async (website) => {
        try {
            await api.post('/ai/add-discovered-website', website);
            message.success(`Website ${website.name} added for monitoring!`);
            setDiscoveredWebsites(prev => prev.filter(w => w.domain !== website.domain));
        } catch (error) {
            message.error('Failed to add website: ' + (error.response?.data?.detail || error.message));
        }
    };

    // Product details modal handlers
    const showProductDetails = (product) => {
        setSelectedProduct(product);
        setDetailsModalVisible(true);
    };

    const handleDetailsModalCancel = () => {
        setDetailsModalVisible(false);
        setSelectedProduct(null);
    };

    // Add data status check
    const checkDataStatus = async () => {
        try {
            const response = await api.get('/data/status');
            setDataStatus(response.data);
        } catch (error) {
            console.error('Failed to check data status:', error);
        }
    };

    // Fetch products from API
    const fetchProducts = async () => {
        setLoading(true);
        try {
            let productsData = [];

            // Always try API first
            try {
                // Use a default search query if none is entered
                const searchQuery = searchText.trim() || 'mobile';
                const response = await api.get(`/products/search?query=${searchQuery}&limit=50`);

                if (response.status === 200 && response.data) {
                    productsData = Array.isArray(response.data) ? response.data : [response.data];
                    console.log(`Successfully fetched ${productsData.length} products from API`);
                    setApiAvailable(true);
                } else {
                    throw new Error('Invalid API response');
                }
            } catch (apiError) {
                console.warn('API call failed:', apiError.message);
                setApiAvailable(false);
                // Use mock data as fallback
                productsData = mockData.products;
            }

            // Process products for table display
            const productsWithKeys = productsData.map((product, index) => ({
                ...product,
                key: product.product_id || `product-${index}`,
                // Ensure all required fields exist
                canonical_title: product.canonical_title || product.title || 'Unknown Product',
                canonical_title_fa: product.canonical_title_fa || product.title_fa || 'محصول نامشخص',
                brand: product.brand || 'Unknown Brand',
                category: product.category || 'mobile',
                lowest_price: product.lowest_price || {
                    price_toman: product.current_prices?.[0]?.price_toman || 0,
                    price_usd: product.current_prices?.[0]?.price_usd || 0,
                    vendor_name_fa: product.current_prices?.[0]?.vendor_name_fa || 'نامشخص'
                },
                available_vendors: product.available_vendors || (product.current_prices ? product.current_prices.length : 0),
                last_updated: product.last_updated || new Date().toISOString()
            }));

            setProducts(productsWithKeys);

            // Calculate stats from real data
            const totalValue = productsWithKeys.reduce((sum, product) =>
                sum + (product.lowest_price?.price_toman || 0), 0
            );

            setStats({
                totalProducts: productsWithKeys.length,
                activeProducts: productsWithKeys.filter(p => p.available_vendors > 0).length,
                totalValue: totalValue
            });

        } catch (error) {
            message.error('Failed to fetch products');
            console.error('Error fetching products:', error);
            setProducts([]);
            setStats({ totalProducts: 0, activeProducts: 0, totalValue: 0 });
        } finally {
            setLoading(false);
        }
    };

    // Add new product
    const handleAddProduct = async (values) => {
        try {
            if (apiAvailable) {
                await productsAPI.addProduct(values);
            } else {
                // Simulate adding product to mock data
                const newProduct = {
                    product_id: `PROD${Date.now()}`,
                    canonical_title: values.canonical_title,
                    canonical_title_fa: values.canonical_title_fa,
                    brand: values.brand,
                    category: values.category,
                    current_prices: [],
                    lowest_price: null,
                    highest_price: null,
                    price_range_pct: 0,
                    available_vendors: 0,
                    last_updated: new Date().toISOString()
                };
                mockData.products.push(newProduct);
            }
            message.success('Product added successfully!');
            setIsModalVisible(false);
            form.resetFields();
            fetchProducts(); // Refresh the list
        } catch (error) {
            message.error('Failed to add product');
            console.error('Error adding product:', error);
        }
    };

    // Delete product
    const handleDeleteProduct = async (productId) => {
        try {
            if (apiAvailable) {
                await productsAPI.deleteProduct(productId);
            } else {
                // Simulate deleting product from mock data
                const index = mockData.products.findIndex(p => p.product_id === productId);
                if (index > -1) {
                    mockData.products.splice(index, 1);
                }
            }
            message.success('Product deleted successfully!');
            fetchProducts(); // Refresh the list
        } catch (error) {
            message.error('Failed to delete product');
            console.error('Error deleting product:', error);
        }
    };

    // Refresh prices
    const handleRefreshPrices = async (productId) => {
        try {
            if (apiAvailable) {
                const refreshResponse = await api.post(`/products/${productId}/refresh-prices`);

                if (refreshResponse.data && refreshResponse.data.status === 'processing') {
                    message.loading('Refreshing prices...');

                    // Give the backend some time to process
                    await new Promise(resolve => setTimeout(resolve, 2000));

                    message.success('Prices refreshed successfully!');
                } else {
                    message.warning('Price refresh initiated but status unclear');
                }
            } else {
                // Simulate price refresh in mock mode
                message.loading('Simulating price refresh...');
                await new Promise(resolve => setTimeout(resolve, 2000));
                message.success('Prices refreshed successfully (mock mode)!');
            }

            // Reload data regardless of whether we're in API or mock mode
            fetchProducts();
        } catch (error) {
            message.error('Failed to refresh prices');
            console.error('Error refreshing prices:', error);
        }
    };

    useEffect(() => {
        // Check API availability and data status on component mount
        const checkAPI = async () => {
            try {
                const healthResponse = await api.get('/health');
                const isAvailable = healthResponse.status === 200 && healthResponse.data.status === 'healthy';
                setApiAvailable(isAvailable);
                console.log("API health check:", isAvailable ? "Connected" : "Disconnected");

                // Also check data status if API is available
                if (isAvailable) {
                    await checkDataStatus();
                }
            } catch (error) {
                console.error("API health check failed:", error);
                setApiAvailable(false);
            }
        };
        checkAPI();

        // Set up periodic data status check
        const interval = setInterval(() => {
            if (apiAvailable) {
                checkDataStatus();
            }
        }, 30000); // Check every 30 seconds

        return () => clearInterval(interval);
    }, [apiAvailable]);

    useEffect(() => {
        fetchProducts();
    }, [searchText, apiAvailable]);

    // Add auto-refresh functionality
    useEffect(() => {
        // Refresh data every 2 minutes when API is available
        let refreshInterval;

        if (apiAvailable) {
            refreshInterval = setInterval(() => {
                console.log('Auto-refreshing product data...');
                fetchProducts();
            }, 120000); // 2 minutes
        }

        return () => {
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }
        };
    }, [apiAvailable, searchText]);

    const columns = [
        {
            title: 'Product ID',
            dataIndex: 'product_id',
            key: 'product_id',
            width: 120,
        },
        {
            title: 'Product Name',
            dataIndex: 'canonical_title',
            key: 'canonical_title',
            render: (text, record) => (
                <div>
                    <div style={{ fontWeight: 'bold' }}>{text}</div>
                    <div style={{ fontSize: '12px', color: '#666' }}>{record.canonical_title_fa}</div>
                    <div style={{ fontSize: '11px', color: '#999' }}>Brand: {record.brand}</div>
                </div>
            ),
        },
        {
            title: 'Category',
            dataIndex: 'category',
            key: 'category',
            width: 100,
            render: (category) => (
                <Tag color="blue">{category.toUpperCase()}</Tag>
            ),
        },
        {
            title: 'Lowest Price',
            key: 'lowest_price',
            width: 150,
            render: (_, record) => (
                <div>
                    <div style={{ fontWeight: 'bold', color: '#52c41a' }}>
                        {record.lowest_price?.price_toman?.toLocaleString()} تومان
                    </div>
                    <div style={{ fontSize: '11px', color: '#999' }}>
                        ${record.lowest_price?.price_usd?.toFixed(0)}
                    </div>
                    <div style={{ fontSize: '10px', color: '#666' }}>
                        {record.lowest_price?.vendor_name_fa}
                    </div>
                </div>
            ),
        },
        {
            title: 'Price Range',
            key: 'price_range',
            width: 120,
            render: (_, record) => (
                <div>
                    <div style={{ fontSize: '12px' }}>
                        {record.price_range_pct > 0 ? (
                            <span style={{ color: '#fa8c16' }}>
                                ±{record.price_range_pct}%
                            </span>
                        ) : (
                            <span style={{ color: '#52c41a' }}>Fixed</span>
                        )}
                    </div>
                    <div style={{ fontSize: '10px', color: '#666' }}>
                        {record.available_vendors} vendors
                    </div>
                </div>
            ),
        },
        {
            title: 'Last Updated',
            dataIndex: 'last_updated',
            key: 'last_updated',
            width: 120,
            render: (date) => (
                <div style={{ fontSize: '11px' }}>
                    {new Date(date).toLocaleDateString('fa-IR')}
                </div>
            ),
        },
        {
            title: 'Actions',
            key: 'actions',
            width: 200,
            render: (_, record) => (
                <Space size="small">
                    <Tooltip title="View Details">
                        <Button
                            type="text"
                            icon={<EyeOutlined />}
                            size="small"
                            onClick={() => showProductDetails(record)}
                        />
                    </Tooltip>
                    <Tooltip title="Refresh Prices">
                        <Button
                            type="text"
                            icon={<ReloadOutlined />}
                            size="small"
                            onClick={() => handleRefreshPrices(record.product_id)}
                        />
                    </Tooltip>
                    <Tooltip title="Edit Product">
                        <Button
                            type="text"
                            icon={<EditOutlined />}
                            size="small"
                            onClick={() => {
                                setEditingProduct(record);
                                setIsModalVisible(true);
                            }}
                        />
                    </Tooltip>
                    <Popconfirm
                        title="Are you sure you want to delete this product?"
                        onConfirm={() => handleDeleteProduct(record.product_id)}
                        okText="Yes"
                        cancelText="No"
                    >
                        <Tooltip title="Delete Product">
                            <Button
                                type="text"
                                danger
                                icon={<DeleteOutlined />}
                                size="small"
                            />
                        </Tooltip>
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div>
            {/* Statistics Cards */}
            <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={8}>
                    <Card>
                        <Statistic
                            title="Total Products"
                            value={stats.totalProducts}
                            prefix={<ShoppingOutlined />}
                            valueStyle={{ color: '#1890ff' }}
                        />
                    </Card>
                </Col>
                <Col span={8}>
                    <Card>
                        <Statistic
                            title="Active Products"
                            value={stats.activeProducts}
                            prefix={<ShoppingOutlined />}
                            valueStyle={{ color: '#52c41a' }}
                        />
                    </Card>
                </Col>
                <Col span={8}>
                    <Card>
                        <Statistic
                            title="Total Value"
                            value={stats.totalValue.toLocaleString()}
                            prefix={<DollarOutlined />}
                            suffix="تومان"
                            valueStyle={{ color: '#fa8c16' }}
                        />
                    </Card>
                </Col>
            </Row>

            <Card
                title="Products Management"
                extra={
                    <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => {
                            setEditingProduct(null);
                            setIsModalVisible(true);
                        }}
                    >
                        Add New Product
                    </Button>
                }
            >
                <Space style={{ marginBottom: 16 }}>
                    <Input
                        placeholder="Search products by name, brand, or category..."
                        prefix={<SearchOutlined />}
                        style={{ width: 400 }}
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                    />
                    <Button
                        icon={<ReloadOutlined />}
                        onClick={fetchProducts}
                        loading={loading}
                    >
                        Refresh
                    </Button>
                    <Button
                        type="primary"
                        icon={<SearchOutlined />}
                        onClick={handleAiDiscovery}
                        loading={aiDiscoveryLoading}
                        style={{ backgroundColor: '#722ed1', borderColor: '#722ed1' }}
                    >
                        🔍 AI Discover Websites
                    </Button>
                </Space>

                {/* Enhanced status indicator */}
                <Alert
                    message={
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span>{dataStatus.real_data_flag ? "🟢 Live Data Active" : "🟡 Demo Mode"}</span>
                            {apiAvailable && (
                                <Button
                                    size="small"
                                    onClick={checkDataStatus}
                                    icon={<ReloadOutlined />}
                                >
                                    Refresh
                                </Button>
                            )}
                        </div>
                    }
                    description={
                        <div>
                            {dataStatus.real_data_flag ? (
                                <div>
                                    Showing live data from {dataStatus.product_count} products across {dataStatus.scraping_summary?.vendors ? JSON.parse(dataStatus.scraping_summary.vendors).length : 0} vendors.
                                    <br />
                                    Last updated: {dataStatus.scraping_summary?.last_updated ? new Date(dataStatus.scraping_summary.last_updated).toLocaleString() : 'Unknown'}
                                </div>
                            ) : (
                                "No real scraped data available. Run the scraper to see live data."
                            )}
                        </div>
                    }
                    type={dataStatus.real_data_flag ? "success" : "warning"}
                    showIcon
                    style={{ marginBottom: 16 }}
                />

                <Table
                    columns={columns}
                    dataSource={products}
                    loading={loading}
                    pagination={{
                        pageSize: 10,
                        showSizeChanger: true,
                        showQuickJumper: true,
                        showTotal: (total, range) =>
                            `${range[0]}-${range[1]} of ${total} products`
                    }}
                    scroll={{ x: 1200 }}
                />
            </Card>

            {/* Add/Edit Product Modal */}
            <Modal
                title={editingProduct ? "Edit Product" : "Add New Product"}
                open={isModalVisible}
                onCancel={() => {
                    setIsModalVisible(false);
                    setEditingProduct(null);
                    form.resetFields();
                }}
                footer={null}
                width={600}
            >
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleAddProduct}
                    initialValues={editingProduct || {}}
                >
                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item
                                name="canonical_title"
                                label="Product Name (English)"
                                rules={[{ required: true, message: 'Please enter product name!' }]}
                            >
                                <Input placeholder="e.g., Samsung Galaxy S21" />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item
                                name="canonical_title_fa"
                                label="Product Name (Persian)"
                                rules={[{ required: true, message: 'Please enter Persian name!' }]}
                            >
                                <Input placeholder="e.g., سامسونگ گلکسی اس ۲۱" />
                            </Form.Item>
                        </Col>
                    </Row>

                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item
                                name="brand"
                                label="Brand"
                                rules={[{ required: true, message: 'Please select brand!' }]}
                            >
                                <Select placeholder="Select brand">
                                    <Option value="Samsung">Samsung</Option>
                                    <Option value="Apple">Apple</Option>
                                    <Option value="Xiaomi">Xiaomi</Option>
                                    <Option value="Huawei">Huawei</Option>
                                    <Option value="Other">Other</Option>
                                </Select>
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item
                                name="category"
                                label="Category"
                                rules={[{ required: true, message: 'Please select category!' }]}
                            >
                                <Select placeholder="Select category">
                                    <Option value="mobile">Mobile</Option>
                                    <Option value="laptop">Laptop</Option>
                                    <Option value="tablet">Tablet</Option>
                                    <Option value="accessories">Accessories</Option>
                                </Select>
                            </Form.Item>
                        </Col>
                    </Row>

                    <Form.Item
                        name="product_url"
                        label="Product URL"
                        rules={[{ required: true, message: 'Please enter product URL!' }]}
                    >
                        <Input placeholder="https://digikala.com/product/..." />
                    </Form.Item>

                    <Form.Item>
                        <Space>
                            <Button type="primary" htmlType="submit">
                                {editingProduct ? 'Update Product' : 'Add Product'}
                            </Button>
                            <Button onClick={() => {
                                setIsModalVisible(false);
                                setEditingProduct(null);
                                form.resetFields();
                            }}>
                                Cancel
                            </Button>
                        </Space>
                    </Form.Item>
                </Form>
            </Modal>

            {/* Product Details Modal */}
            <Modal
                title={
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <EyeOutlined style={{ color: '#1890ff' }} />
                        <span>Product Details</span>
                        {selectedProduct && (
                            <Tag color="blue">{selectedProduct.category?.toUpperCase()}</Tag>
                        )}
                    </div>
                }
                open={detailsModalVisible}
                onCancel={handleDetailsModalCancel}
                footer={[
                    <Button key="close" onClick={handleDetailsModalCancel}>
                        Close
                    </Button>
                ]}
                width={800}
                destroyOnClose
            >
                {selectedProduct && (
                    <div style={{ padding: '20px 0' }}>
                        {/* Product Header */}
                        <div style={{ marginBottom: '24px', padding: '16px', background: '#f6f8fa', borderRadius: '8px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                <div>
                                    <h2 style={{ margin: '0 0 8px 0', fontSize: '20px', fontWeight: 'bold' }}>
                                        {selectedProduct.canonical_title}
                                    </h2>
                                    <p style={{ margin: '0', color: '#666', fontSize: '16px' }}>
                                        {selectedProduct.canonical_title_fa}
                                    </p>
                                    <div style={{ marginTop: '8px' }}>
                                        <Tag color="geekblue">{selectedProduct.brand}</Tag>
                                        <Tag color="cyan">{selectedProduct.category}</Tag>
                                        <Tag color="purple">{selectedProduct.product_id}</Tag>
                                    </div>
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                    <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>
                                        Last Updated
                                    </div>
                                    <div style={{ fontSize: '14px' }}>
                                        {new Date(selectedProduct.last_updated).toLocaleString('fa-IR')}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <Row gutter={24}>
                            {/* Price Information */}
                            <Col span={12}>
                                <Card title="Price Information" size="small">
                                    <div style={{ marginBottom: '16px' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                            <span>Lowest Price:</span>
                                            <strong style={{ color: '#52c41a' }}>
                                                {selectedProduct.lowest_price?.price_toman?.toLocaleString()} تومان
                                            </strong>
                                        </div>
                                        <div style={{ fontSize: '12px', color: '#666', marginBottom: '16px' }}>
                                            {selectedProduct.lowest_price?.vendor_name_fa} - ${selectedProduct.lowest_price?.price_usd?.toFixed(2)}
                                        </div>
                                    </div>

                                    {selectedProduct.highest_price && selectedProduct.highest_price.price_toman !== selectedProduct.lowest_price?.price_toman && (
                                        <div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                                <span>Highest Price:</span>
                                                <strong style={{ color: '#fa8c16' }}>
                                                    {selectedProduct.highest_price.price_toman?.toLocaleString()} تومان
                                                </strong>
                                            </div>
                                            <div style={{ fontSize: '12px', color: '#666' }}>
                                                {selectedProduct.highest_price.vendor_name_fa} - ${selectedProduct.highest_price.price_usd?.toFixed(2)}
                                            </div>
                                        </div>
                                    )}

                                    <Divider />
                                    <div style={{ textAlign: 'center' }}>
                                        <div style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '4px' }}>
                                            Price Range: {selectedProduct.price_range_pct}%
                                        </div>
                                        <div style={{ fontSize: '12px', color: '#666' }}>
                                            Available from {selectedProduct.available_vendors} vendor(s)
                                        </div>
                                    </div>
                                </Card>
                            </Col>

                            {/* Product Details */}
                            <Col span={12}>
                                <Card title="Product Information" size="small">
                                    <div style={{ marginBottom: '12px' }}>
                                        <strong>Model:</strong> {selectedProduct.model || 'N/A'}
                                    </div>
                                    <div style={{ marginBottom: '12px' }}>
                                        <strong>Product ID:</strong> {selectedProduct.product_id}
                                    </div>
                                    <div style={{ marginBottom: '12px' }}>
                                        <strong>Category:</strong> {selectedProduct.category}
                                    </div>
                                    <div style={{ marginBottom: '12px' }}>
                                        <strong>Brand:</strong> {selectedProduct.brand}
                                    </div>
                                </Card>
                            </Col>
                        </Row>

                        {/* Vendor Prices */}
                        <Card title="Available Vendors" style={{ marginTop: '24px' }} size="small">
                            <div style={{ display: 'grid', gap: '12px' }}>
                                {selectedProduct.current_prices && selectedProduct.current_prices.map((price, index) => (
                                    <div key={index} style={{
                                        padding: '12px',
                                        border: '1px solid #f0f0f0',
                                        borderRadius: '8px',
                                        background: price.price_toman === selectedProduct.lowest_price?.price_toman ? '#f6ffed' : 'white'
                                    }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <div>
                                                <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                                                    {price.vendor_name_fa}
                                                </div>
                                                <div style={{ fontSize: '12px', color: '#666' }}>
                                                    {price.vendor}
                                                </div>
                                                {price.vendor && (
                                                    <div>
                                                        <a
                                                            href={`https://${price.vendor}`}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            style={{ fontSize: '12px', color: '#1890ff', textDecoration: 'none' }}
                                                        >
                                                            🏪 Visit Store →
                                                        </a>
                                                        {price.product_url && price.product_url !== `https://${price.vendor}/product/mobile/1` && price.product_url !== `https://${price.vendor}/product/mobile/2` && (
                                                            <a
                                                                href={price.product_url}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                style={{ fontSize: '12px', color: '#52c41a', marginLeft: '8px' }}
                                                            >
                                                                📱 View Product →
                                                            </a>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                            <div style={{ textAlign: 'right' }}>
                                                <div style={{
                                                    fontSize: '18px',
                                                    fontWeight: 'bold',
                                                    color: price.price_toman === selectedProduct.lowest_price?.price_toman ? '#52c41a' : '#fa8c16'
                                                }}>
                                                    {price.price_toman?.toLocaleString()} تومان
                                                </div>
                                                <div style={{ fontSize: '12px', color: '#666' }}>
                                                    ${price.price_usd?.toFixed(2)} USD
                                                </div>
                                                <div style={{ marginTop: '4px' }}>
                                                    <Tag color={price.availability ? 'success' : 'error'}>
                                                        {price.availability ? 'Available' : 'Out of Stock'}
                                                    </Tag>
                                                </div>
                                            </div>
                                        </div>
                                        <div style={{ marginTop: '8px', fontSize: '11px', color: '#999' }}>
                                            Updated: {new Date(price.last_updated).toLocaleString('fa-IR')}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </Card>
                    </div>
                )}
            </Modal>

            {/* AI Website Discovery Modal */}
            <Modal
                title={
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span>🤖 AI Website Discovery</span>
                        <Tag color="purple">Beta</Tag>
                    </div>
                }
                open={aiDiscoveryVisible}
                onCancel={() => setAiDiscoveryVisible(false)}
                width={800}
                footer={[
                    <Button key="close" onClick={() => setAiDiscoveryVisible(false)}>
                        Close
                    </Button>
                ]}
            >
                <div style={{ marginBottom: '16px' }}>
                    <Alert
                        message="AI-Powered Website Discovery"
                        description="Our AI has analyzed web sources to find potential Iranian e-commerce websites. High-confidence sites are recommended for monitoring."
                        type="info"
                        showIcon
                    />
                </div>

                {discoveredWebsites.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                        <p>No websites discovered yet. Click "AI Discover Websites" to start the discovery process.</p>
                    </div>
                ) : (
                    <div>
                        {discoveredWebsites.map((website, index) => (
                            <Card
                                key={index}
                                size="small"
                                style={{
                                    marginBottom: '12px',
                                    border: website.confidence_score > 0.8 ? '2px solid #52c41a' : '1px solid #d9d9d9'
                                }}
                            >
                                <Row gutter={16} align="middle">
                                    <Col span={16}>
                                        <div>
                                            <h4 style={{ margin: '0 0 8px 0' }}>
                                                {website.name}
                                                {website.confidence_score > 0.8 && (
                                                    <Tag color="green" style={{ marginLeft: '8px' }}>High Confidence</Tag>
                                                )}
                                                {website.category !== 'unknown' && (
                                                    <Tag color="blue" style={{ marginLeft: '8px' }}>{website.category}</Tag>
                                                )}
                                            </h4>
                                            <p style={{ margin: '0 0 4px 0', color: '#666' }}>{website.url}</p>
                                            <p style={{ margin: '0', fontSize: '12px', color: '#999' }}>
                                                Confidence: {(website.confidence_score * 100).toFixed(1)}% |
                                                Indicators: {website.indicators.join(', ')}
                                            </p>
                                        </div>
                                    </Col>
                                    <Col span={8} style={{ textAlign: 'right' }}>
                                        <Space direction="vertical" size="small">
                                            <Button
                                                type="primary"
                                                size="small"
                                                onClick={() => addDiscoveredWebsite(website)}
                                                style={{ backgroundColor: '#52c41a', borderColor: '#52c41a' }}
                                            >
                                                ➕ Add to Monitoring
                                            </Button>
                                            <Button
                                                type="link"
                                                size="small"
                                                href={website.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                            >
                                                🌐 Visit Site
                                            </Button>
                                        </Space>
                                    </Col>
                                </Row>
                            </Card>
                        ))}
                    </div>
                )}
            </Modal>
        </div>
    );
};

export default Products;
