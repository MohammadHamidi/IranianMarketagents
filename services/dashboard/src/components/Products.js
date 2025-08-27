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

    // Fetch products from API
    const fetchProducts = async () => {
        setLoading(true);
        try {
            let productsData = [];
            
            if (apiAvailable) {
                // Try to fetch from real API with better error handling
                try {
                    // Provide a default search query if none is entered
                    const searchQuery = searchText.trim() || 'mobile'; // Default to 'mobile' if empty
                    const response = await api.get(`/products/search?query=${searchQuery}&limit=100`);
                    
                    if (response.status === 200) {
                        productsData = response.data;
                        console.log(`Successfully fetched ${productsData.length} products from API`);
                    } else {
                        console.warn('API returned non-200 status, falling back to mock data');
                        productsData = mockData.products;
                    }
                } catch (apiError) {
                    console.warn('API call failed, falling back to mock data:', apiError.message);
                    productsData = mockData.products;
                }
            } else {
                // Use mock data
                console.log('API unavailable, using mock data');
                productsData = mockData.products;
            }

            // Add keys for table
            const productsWithKeys = productsData.map((product, index) => ({
                ...product,
                key: product.product_id || `product-${index}`
            }));

            setProducts(productsWithKeys);
            
            // Calculate stats
            const totalValue = productsData.reduce((sum, product) => 
                sum + (product.lowest_price?.price_toman || 0), 0
            );
            
            setStats({
                totalProducts: productsData.length,
                activeProducts: productsData.filter(p => p.available_vendors > 0).length,
                totalValue: totalValue
            });

        } catch (error) {
            message.error('Failed to fetch products');
            console.error('Error fetching products:', error);
            // In case of total failure, use empty array
            setProducts([]);
            setStats({
                totalProducts: 0,
                activeProducts: 0,
                totalValue: 0
            });
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
        // Check API availability on component mount
        const checkAPI = async () => {
            try {
                const healthResponse = await api.get('/health');
                const isAvailable = healthResponse.status === 200 && healthResponse.data.status === 'healthy';
                setApiAvailable(isAvailable);
                console.log("API health check:", isAvailable ? "Connected" : "Disconnected");
            } catch (error) {
                console.error("API health check failed:", error);
                setApiAvailable(false);
            }
        };
        checkAPI();
    }, []);

    useEffect(() => {
        fetchProducts();
    }, [searchText, apiAvailable]);

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
                            onClick={() => message.info('View details feature coming soon!')}
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
                </Space>

                <Alert
                    message={apiAvailable ? "Real-time Price Monitoring" : "Demo Mode - Using Mock Data"}
                    description={apiAvailable
                        ? (searchText.trim() === ""
                            ? "Showing products for 'mobile' category. Enter a search term to filter results."
                            : `Showing products matching: "${searchText}"`
                          )
                        : "Currently running in demo mode with mock data. Connect to the API to see real data."
                    }
                    type={apiAvailable ? "info" : "warning"}
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
        </div>
    );
};

export default Products;
