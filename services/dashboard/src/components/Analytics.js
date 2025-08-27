import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Button, Select, Alert, Space, Tabs, Form, Input, message } from 'antd';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../services/api';
import { RobotOutlined, SearchOutlined, BarChartOutlined, ThunderboltOutlined, PlusOutlined } from '@ant-design/icons';

const { Option } = Select;
const { TextArea } = Input;
const { TabPane } = Tabs;

const Analytics = () => {
    const [analyticsData, setAnalyticsData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [aiLoading, setAiLoading] = useState(false);
    const [aiResults, setAiResults] = useState(null);
    const [aiAgents, setAiAgents] = useState([]);
    const [selectedCategory, setSelectedCategory] = useState('mobile');
    const [priceData, setPriceData] = useState([]);
    const [newProduct, setNewProduct] = useState({
        title: '',
        title_fa: '',
        category: 'mobile',
        vendor_urls: []
    });

    useEffect(() => {
        fetchAnalytics();
        checkAIAgents();
        fetchPriceData();
    }, []);

    const fetchAnalytics = async () => {
        try {
            setLoading(true);
            // Get real analytics data from the dedicated analytics endpoint
            const response = await api.get('/analytics/dashboard');

            if (response.data) {
                // Use the structured analytics data directly from the API
                setAnalyticsData({
                    totalProducts: response.data.totalProducts || 0,
                    activeVendors: response.data.activeVendors || 0,
                    priceChangesToday: response.data.priceChangesToday || 0,
                    avgPriceChangePercent: response.data.avgPriceChangePercent || 0,
                    avgPrice: response.data.avgPrice || 0,
                    topVendors: response.data.topVendors || [],
                    categories: response.data.categories || [],
                    lastUpdated: response.data.lastUpdated || new Date().toISOString()
                });
            } else {
                // Fallback to empty data if no analytics found
                setAnalyticsData({
                    totalProducts: 0,
                    activeVendors: 0,
                    priceChangesToday: 0,
                    avgPriceChangePercent: 0,
                    avgPrice: 0,
                    topVendors: [],
                    categories: [],
                    lastUpdated: new Date().toISOString()
                });
            }
        } catch (error) {
            console.error('Error fetching analytics:', error);
            // Use mock data if API fails
            setAnalyticsData({
                totalProducts: 21,
                activeVendors: 3,
                priceChangesToday: 8,
                avgPriceChangePercent: 3.2,
                avgPrice: 25000000,
                topVendors: ['Digikala', 'Technolife', 'Snap'],
                categories: ['mobile', 'laptop', 'electronics'],
                lastUpdated: new Date().toISOString()
            });
        } finally {
            setLoading(false);
        }
    };

    const checkAIAgents = async () => {
        try {
            const response = await api.get('/ai/agents/status');
            if (response.data.status === 'active') {
                setAiAgents(response.data.agents);
            }
        } catch (error) {
            console.error('AI agents not available:', error);
        }
    };

    const runProductDiscovery = async () => {
        try {
            setAiLoading(true);
            const response = await api.post('/ai/discover-products', {
                category: selectedCategory,
                limit: 5
            });
            setAiResults(response.data);
            message.success('🤖 AI product discovery completed!');
        } catch (error) {
            console.error('Error in AI discovery:', error);
            message.error('AI discovery failed');
        } finally {
            setAiLoading(false);
        }
    };

    const runPriceAnalysis = async () => {
        try {
            setAiLoading(true);
            const response = await api.post('/ai/analyze-prices');
            setAiResults(response.data);
            message.success('🤖 AI price analysis completed!');
        } catch (error) {
            console.error('Error in AI analysis:', error);
            message.error('AI analysis failed');
        } finally {
            setAiLoading(false);
        }
    };

    const getMarketIntelligence = async () => {
        try {
            setAiLoading(true);
            const response = await api.post('/ai/market-intelligence', {
                focus_area: 'pricing'
            });
            setAiResults(response.data);
            message.success('🤖 Market intelligence gathered!');
        } catch (error) {
            console.error('Error getting market intelligence:', error);
            message.error('Market intelligence failed');
        } finally {
            setAiLoading(false);
        }
    };

    const addProductViaAI = async () => {
        if (!newProduct.title) {
            message.error('Please enter a product title');
            return;
        }

        try {
            setAiLoading(true);
            const response = await api.post('/ai/add-product', newProduct);
            setAiResults(response.data);
            message.success('🤖 Product added via AI!');
            setNewProduct({ title: '', title_fa: '', category: 'mobile', vendor_urls: [] });
        } catch (error) {
            console.error('Error adding product via AI:', error);
            message.error('Failed to add product');
        } finally {
            setAiLoading(false);
        }
    };

    const autoOptimize = async () => {
        try {
            setAiLoading(true);
            const response = await api.post('/ai/auto-optimize');
            setAiResults(response.data);
            message.success('🤖 System optimization completed!');
        } catch (error) {
            console.error('Error in auto optimization:', error);
            message.error('Optimization failed');
        } finally {
            setAiLoading(false);
        }
    };

    const stats = analyticsData ? [
        { title: 'Total Products', value: analyticsData.totalProducts, prefix: '📦' },
        { title: 'Active Vendors', value: analyticsData.activeVendors, prefix: '🏪' },
        { title: 'Price Changes Today', value: analyticsData.priceChangesToday, prefix: '💰' },
        { title: 'AI Agents Active', value: aiAgents.length, prefix: '🤖' },
    ] : [
        { title: 'Total Products', value: 0, prefix: '📦' },
        { title: 'Active Vendors', value: 0, prefix: '🏪' },
        { title: 'Price Changes Today', value: 0, prefix: '💰' },
        { title: 'AI Agents Active', value: aiAgents.length, prefix: '🤖' },
    ];

    const renderAIAgentPanel = () => (
        <Card title={<><RobotOutlined /> AI Agent Control Panel</>} style={{ marginTop: 16 }}>
            <Tabs defaultActiveKey="1">
                <TabPane tab={<><SearchOutlined /> Product Discovery</>} key="1">
                    <Space direction="vertical" style={{ width: '100%' }}>
                        <Alert
                            message="🤖 AI Product Discovery"
                            description="Let AI find trending products and price opportunities in the Iranian market"
                            type="info"
                            showIcon
                        />
                        <Space>
                            <Select
                                value={selectedCategory}
                                onChange={setSelectedCategory}
                                style={{ width: 200 }}
                            >
                                <Option value="mobile">Mobile Phones</Option>
                                <Option value="laptop">Laptops</Option>
                                <Option value="tablet">Tablets</Option>
                                <Option value="electronics">Electronics</Option>
                            </Select>
                            <Button
                                type="primary"
                                icon={<SearchOutlined />}
                                loading={aiLoading}
                                onClick={runProductDiscovery}
                            >
                                Discover Products
                            </Button>
                        </Space>
                    </Space>
                </TabPane>

                <TabPane tab={<><BarChartOutlined /> Price Analysis</>} key="2">
                    <Space direction="vertical" style={{ width: '100%' }}>
                        <Alert
                            message="🤖 AI Price Analysis"
                            description="AI analyzes price volatility, gaps, and market opportunities"
                            type="info"
                            showIcon
                        />
                        <Button
                            type="primary"
                            icon={<BarChartOutlined />}
                            loading={aiLoading}
                            onClick={runPriceAnalysis}
                        >
                            Analyze Prices
                        </Button>
                    </Space>
                </TabPane>

                <TabPane tab={<><ThunderboltOutlined /> Market Intelligence</>} key="3">
                    <Space direction="vertical" style={{ width: '100%' }}>
                        <Alert
                            message="🤖 Market Intelligence"
                            description="Get AI-powered insights about Iranian e-commerce market trends"
                            type="info"
                            showIcon
                        />
                        <Button
                            type="primary"
                            icon={<ThunderboltOutlined />}
                            loading={aiLoading}
                            onClick={getMarketIntelligence}
                        >
                            Get Intelligence
                        </Button>
                    </Space>
                </TabPane>

                <TabPane tab={<><PlusOutlined /> Add Product</>} key="4">
                    <Space direction="vertical" style={{ width: '100%' }}>
                        <Alert
                            message="🤖 AI Product Addition"
                            description="AI helps you add new products to monitor"
                            type="info"
                            showIcon
                        />
                        <Form layout="vertical">
                            <Form.Item label="Product Title (English)">
                                <Input
                                    placeholder="e.g., Samsung Galaxy S25"
                                    value={newProduct.title}
                                    onChange={(e) => setNewProduct({...newProduct, title: e.target.value})}
                                />
                            </Form.Item>
                            <Form.Item label="Product Title (Persian)">
                                <Input
                                    placeholder="e.g., سامسونگ گلکسی اس ۲۵"
                                    value={newProduct.title_fa}
                                    onChange={(e) => setNewProduct({...newProduct, title_fa: e.target.value})}
                                />
                            </Form.Item>
                            <Form.Item label="Category">
                                <Select
                                    value={newProduct.category}
                                    onChange={(value) => setNewProduct({...newProduct, category: value})}
                                >
                                    <Option value="mobile">Mobile Phones</Option>
                                    <Option value="laptop">Laptops</Option>
                                    <Option value="tablet">Tablets</Option>
                                    <Option value="electronics">Electronics</Option>
                                </Select>
                            </Form.Item>
                            <Form.Item>
                                <Button
                                    type="primary"
                                    icon={<PlusOutlined />}
                                    loading={aiLoading}
                                    onClick={addProductViaAI}
                                >
                                    Add Product via AI
                                </Button>
                            </Form.Item>
                        </Form>
                    </Space>
                </TabPane>

                <TabPane tab="System Optimization" key="5">
                    <Space direction="vertical" style={{ width: '100%' }}>
                        <Alert
                            message="🤖 System Optimization"
                            description="AI optimizes system performance, scheduling, and resources"
                            type="info"
                            showIcon
                        />
                        <Button
                            type="primary"
                            icon={<ThunderboltOutlined />}
                            loading={aiLoading}
                            onClick={autoOptimize}
                        >
                            Auto Optimize System
                        </Button>
                    </Space>
                </TabPane>
            </Tabs>
        </Card>
    );

    const renderAIResults = () => {
        if (!aiResults) return null;

        return (
            <Card title="🤖 AI Results" style={{ marginTop: 16 }}>
                <pre style={{
                    backgroundColor: '#f5f5f5',
                    padding: '16px',
                    borderRadius: '4px',
                    overflow: 'auto',
                    maxHeight: '400px'
                }}>
                    {JSON.stringify(aiResults, null, 2)}
                </pre>
            </Card>
        );
    };

    if (loading) {
        return <div>Loading analytics...</div>;
    }

    return (
        <div>
            <h1>🤖 AI-Enhanced Analytics</h1>

            <Row gutter={16} style={{ marginBottom: '24px' }}>
                {stats.map((stat, index) => (
                    <Col span={6} key={index}>
                        <Card>
                            <Statistic
                                title={stat.title}
                                value={stat.value}
                                prefix={stat.prefix}
                                valueStyle={{ color: '#3f8600' }}
                            />
                        </Card>
                    </Col>
                ))}
            </Row>

            <Row gutter={16}>
                <Col span={24}>
                    <Card title="Price Trend Analysis">
                        <ResponsiveContainer width="100%" height={400}>
                            <LineChart data={priceData}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" />
                                <YAxis />
                                <Tooltip formatter={(value) => `${value.toLocaleString()} تومان`} />
                                <Line type="monotone" dataKey="price" stroke="#8884d8" strokeWidth={2} />
                            </LineChart>
                        </ResponsiveContainer>
                    </Card>
                </Col>
            </Row>

            {aiAgents.length > 0 && renderAIAgentPanel()}
            {aiResults && renderAIResults()}
        </div>
    );

    // Fetch real price trend data
    async function fetchPriceData() {
        try {
            // Get price history for a popular product (iPhone 15 Pro)
            const response = await api.get('/products/PROD001/history?days=30');
            
            if (response.data && response.data.history && response.data.history.length > 0) {
                // Transform API data to the format needed for the chart
                const formattedPriceData = response.data.history.map(item => ({
                    date: new Date(item.recorded_at).toISOString().split('T')[0],
                    price: item.price_toman
                }));
                
                setPriceData(formattedPriceData);
                console.log("Price trend data loaded successfully:", formattedPriceData.length, "data points");
            } else {
                // Fallback to demo data if API returns no data
                const demoData = [
                    { date: '2025-01-01', price: 25000000 },
                    { date: '2025-01-02', price: 24800000 },
                    { date: '2025-01-03', price: 25200000 },
                    { date: '2025-01-04', price: 25500000 },
                    { date: '2025-01-05', price: 25300000 },
                    { date: '2025-01-06', price: 25600000 },
                    { date: '2025-01-07', price: 25800000 },
                ];
                
                setPriceData(demoData);
                console.log("Using demo price trend data");
            }
        } catch (error) {
            console.error("Failed to fetch price trend data:", error);
            // Set fallback data on error
            const fallbackData = [
                { date: '2025-01-01', price: 25000000 },
                { date: '2025-01-02', price: 24800000 },
                { date: '2025-01-03', price: 25200000 },
                { date: '2025-01-04', price: 25500000 },
                { date: '2025-01-05', price: 25300000 },
                { date: '2025-01-06', price: 25600000 },
                { date: '2025-01-07', price: 25800000 },
            ];
            
            setPriceData(fallbackData);
        }
    }
};

export default Analytics;
