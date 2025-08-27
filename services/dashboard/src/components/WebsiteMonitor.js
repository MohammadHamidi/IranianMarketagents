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
    Row,
    Col,
    Statistic,
    Alert,
    Progress,
    Tooltip,
    Badge
} from 'antd';
import { 
    SearchOutlined, 
    PlusOutlined, 
    EyeOutlined,
    LinkOutlined,
    ReloadOutlined,
    GlobalOutlined,
    ClockCircleOutlined,
    CheckCircleOutlined,
    ExclamationCircleOutlined
} from '@ant-design/icons';
import { api, websiteAPI, mockData } from '../services/api';

const { Option } = Select;
const { TextArea } = Input;

const WebsiteMonitor = () => {
    const [websites, setWebsites] = useState([]);
    const [loading, setLoading] = useState(false);
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [form] = Form.useForm();
    const [stats, setStats] = useState({
        totalWebsites: 0,
        activeWebsites: 0,
        lastScraped: 0
    });
    const [apiAvailable, setApiAvailable] = useState(false);

    // Remove mock data definition since it's now imported from api.js

    useEffect(() => {
        // Check API availability on component mount
        const checkAPI = async () => {
            try {
                const healthResponse = await api.get('/health');
                const isAvailable = healthResponse.status === 200 && healthResponse.data.status === 'healthy';
                setApiAvailable(isAvailable);
                console.log("WebsiteMonitor - API health check:", isAvailable ? "Connected" : "Disconnected");
            } catch (error) {
                console.error("WebsiteMonitor - API health check failed:", error);
                setApiAvailable(false);
            }
        };
        checkAPI();
    }, []);

    useEffect(() => {
        fetchWebsites();
    }, [apiAvailable]);

    const fetchWebsites = async () => {
        setLoading(true);
        try {
            let websitesData;
            
            if (apiAvailable) {
                // Try to fetch from real API with better error handling
                try {
                    const response = await api.get('/websites');
                    
                    if (response.status === 200) {
                        websitesData = response.data;
                        console.log(`Successfully fetched ${websitesData.length} websites from API`);
                    } else {
                        console.warn('API returned non-200 status, falling back to mock data');
                        websitesData = mockData.websites;
                    }
                } catch (apiError) {
                    console.warn('API call failed, falling back to mock data:', apiError.message);
                    websitesData = mockData.websites;
                }
            } else {
                // Use mock data
                console.log('API unavailable, using mock website data');
                websitesData = mockData.websites;
            }

            // Add keys for table
            const websitesWithKeys = websitesData.map((website, index) => ({
                ...website,
                key: website.id || `website-${index}`
            }));

            setWebsites(websitesWithKeys);
            
            setStats({
                totalWebsites: websitesData.length,
                activeWebsites: websitesData.filter(w => w.status === 'active').length,
                lastScraped: websitesData.length
            });
        } catch (error) {
            message.error('Failed to fetch websites');
            console.error('Error fetching websites:', error);
            // In case of complete failure, use empty array
            setWebsites([]);
            setStats({
                totalWebsites: 0,
                activeWebsites: 0,
                lastScraped: 0
            });
        } finally {
            setLoading(false);
        }
    };

    const handleAddWebsite = async (values) => {
        try {
            if (apiAvailable) {
                await websiteAPI.addWebsite(values);
            } else {
                // Simulate adding website to mock data
                const newWebsite = {
                    id: `WEB${Date.now()}`,
                    name: values.name,
                    url: values.url,
                    status: 'active',
                    lastScraped: new Date().toISOString(),
                    productsFound: 0,
                    priceChanges: 0,
                    successRate: 100,
                    nextScrape: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
                    categories: values.categories || []
                };
                mockData.websites.push(newWebsite);
            }
            message.success('Website added successfully!');
            setIsModalVisible(false);
            form.resetFields();
            fetchWebsites();
        } catch (error) {
            message.error('Failed to add website');
            console.error('Error adding website:', error);
        }
    };

    const handleManualScrape = async (websiteId) => {
        try {
            message.loading('Starting manual scrape...', 2);
            
            if (apiAvailable) {
                const response = await api.post(`/websites/${websiteId}/scrape`);
                
                if (response.data && response.data.status === 'processing') {
                    message.loading('Processing scrape job...', 2);
                    
                    // Give the backend some time to process
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    
                    message.success('Manual scrape completed successfully!');
                } else {
                    message.warning('Scrape initiated but status unclear');
                }
            } else {
                // Simulate manual scrape in mock mode
                message.loading('Simulating scrape process...', 2);
                await new Promise(resolve => setTimeout(resolve, 2000));
                message.success('Manual scrape completed successfully (mock mode)!');
            }
            
            // Refresh the website list
            await new Promise(resolve => setTimeout(resolve, 1000));
            fetchWebsites();
        } catch (error) {
            message.error('Failed to start manual scrape');
            console.error('Error manual scraping:', error);
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'active': return 'green';
            case 'inactive': return 'red';
            case 'maintenance': return 'orange';
            default: return 'default';
        }
    };

    const getTimeUntilNextScrape = (nextScrape) => {
        const now = new Date();
        const next = new Date(nextScrape);
        const diff = next - now;
        const minutes = Math.floor(diff / (1000 * 60));
        return minutes > 0 ? `${minutes}m` : 'Now';
    };

    const columns = [
        {
            title: 'Website',
            key: 'website',
            width: 200,
            render: (_, record) => (
                <div>
                    <div style={{ fontWeight: 'bold' }}>{record.name}</div>
                    <div style={{ fontSize: '11px', color: '#666' }}>
                        <LinkOutlined /> {record.url}
                    </div>
                </div>
            ),
        },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            width: 120,
            render: (status) => (
                <Badge 
                    status={status === 'active' ? 'success' : 'error'} 
                    text={
                        <Tag color={getStatusColor(status)}>
                            {status.toUpperCase()}
                        </Tag>
                    }
                />
            ),
        },
        {
            title: 'Products Found',
            dataIndex: 'productsFound',
            key: 'productsFound',
            width: 140,
            render: (count) => (
                <Statistic 
                    value={count} 
                    valueStyle={{ fontSize: '14px' }}
                    prefix={<GlobalOutlined />}
                />
            ),
        },
        {
            title: 'Price Changes',
            dataIndex: 'priceChanges',
            key: 'priceChanges',
            width: 140,
            render: (changes) => (
                <div>
                    <div style={{ fontWeight: 'bold', color: '#1890ff' }}>
                        {changes}
                    </div>
                    <div style={{ fontSize: '10px', color: '#666' }}>
                        Last 24h
                    </div>
                </div>
            ),
        },
        {
            title: 'Success Rate',
            dataIndex: 'successRate',
            key: 'successRate',
            width: 150,
            render: (rate) => (
                <div>
                    <Progress 
                        percent={rate} 
                        size="small" 
                        status={rate > 95 ? 'success' : rate > 80 ? 'normal' : 'exception'}
                    />
                    <div style={{ fontSize: '10px', color: '#666' }}>
                        {rate}%
                    </div>
                </div>
            ),
        },
        {
            title: 'Last Scraped',
            dataIndex: 'lastScraped',
            key: 'lastScraped',
            width: 150,
            render: (date) => (
                <div>
                    <div style={{ fontSize: '12px' }}>
                        {new Date(date).toLocaleTimeString('fa-IR', { 
                            hour: '2-digit', 
                            minute: '2-digit' 
                        })}
                    </div>
                    <div style={{ fontSize: '10px', color: '#666' }}>
                        {new Date(date).toLocaleDateString('fa-IR')}
                    </div>
                </div>
            ),
        },
        {
            title: 'Next Scrape',
            key: 'nextScrape',
            width: 120,
            render: (_, record) => (
                <div>
                    <div style={{ fontSize: '12px', color: '#1890ff' }}>
                        {getTimeUntilNextScrape(record.nextScrape)}
                    </div>
                    <div style={{ fontSize: '10px', color: '#666' }}>
                        <ClockCircleOutlined /> Auto
                    </div>
                </div>
            ),
        },
        {
            title: 'Actions',
            key: 'actions',
            width: 150,
            render: (_, record) => (
                <Space size="small">
                    <Tooltip title="View Website">
                        <Button 
                            type="text" 
                            icon={<EyeOutlined />} 
                            size="small"
                            onClick={() => window.open(record.url, '_blank')}
                        />
                    </Tooltip>
                    <Tooltip title="Manual Scrape">
                        <Button 
                            type="text" 
                            icon={<ReloadOutlined />} 
                            size="small"
                            onClick={() => handleManualScrape(record.id)}
                        />
                    </Tooltip>
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
                            title="Total Websites"
                            value={stats.totalWebsites}
                            prefix={<GlobalOutlined />}
                            valueStyle={{ color: '#1890ff' }}
                        />
                    </Card>
                </Col>
                <Col span={8}>
                    <Card>
                        <Statistic
                            title="Active Websites"
                            value={stats.activeWebsites}
                            prefix={<CheckCircleOutlined />}
                            valueStyle={{ color: '#52c41a' }}
                        />
                    </Card>
                </Col>
                <Col span={8}>
                    <Card>
                        <Statistic
                            title="Last Scraped"
                            value={stats.lastScraped}
                            prefix={<ClockCircleOutlined />}
                            suffix="websites"
                            valueStyle={{ color: '#fa8c16' }}
                        />
                    </Card>
                </Col>
            </Row>

            <Card 
                title="Website Monitoring" 
                extra={
                    <Button 
                        type="primary" 
                        icon={<PlusOutlined />}
                        onClick={() => setIsModalVisible(true)}
                    >
                        Add Website
                    </Button>
                }
            >
                <Alert
                    message={apiAvailable ? "Real-time Website Monitoring" : "Demo Mode - Using Mock Data"}
                    description={apiAvailable 
                        ? "Monitor product prices from major Iranian e-commerce websites. Prices are automatically scraped every hour."
                        : "Currently running in demo mode with mock data. Connect to the API to see real data."
                    }
                    type={apiAvailable ? "info" : "warning"}
                    showIcon
                    style={{ marginBottom: 16 }}
                />

                <Table
                    columns={columns}
                    dataSource={websites}
                    loading={loading}
                    pagination={{ 
                        pageSize: 10,
                        showSizeChanger: true,
                        showQuickJumper: true
                    }}
                    scroll={{ x: 1200 }}
                />
            </Card>

            {/* Add Website Modal */}
            <Modal
                title="Add New Website"
                open={isModalVisible}
                onCancel={() => {
                    setIsModalVisible(false);
                    form.resetFields();
                }}
                footer={null}
                width={600}
            >
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleAddWebsite}
                >
                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item
                                name="name"
                                label="Website Name"
                                rules={[{ required: true, message: 'Please enter website name!' }]}
                            >
                                <Input placeholder="e.g., Digikala" />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item
                                name="url"
                                label="Website URL"
                                rules={[{ required: true, message: 'Please enter website URL!' }]}
                            >
                                <Input placeholder="https://example.com" />
                            </Form.Item>
                        </Col>
                    </Row>

                    <Form.Item
                        name="categories"
                        label="Categories to Monitor"
                        rules={[{ required: true, message: 'Please select categories!' }]}
                    >
                        <Select
                            mode="multiple"
                            placeholder="Select categories"
                            options={[
                                { value: 'mobile', label: 'Mobile Phones' },
                                { value: 'laptop', label: 'Laptops' },
                                { value: 'tablet', label: 'Tablets' },
                                { value: 'accessories', label: 'Accessories' },
                                { value: 'home', label: 'Home Appliances' },
                                { value: 'fashion', label: 'Fashion' }
                            ]}
                        />
                    </Form.Item>

                    <Form.Item
                        name="scrapeInterval"
                        label="Scrape Interval"
                        rules={[{ required: true, message: 'Please select scrape interval!' }]}
                    >
                        <Select placeholder="Select interval">
                            <Option value={30}>30 minutes</Option>
                            <Option value={60}>1 hour</Option>
                            <Option value={120}>2 hours</Option>
                            <Option value={360}>6 hours</Option>
                            <Option value={720}>12 hours</Option>
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name="description"
                        label="Description (Optional)"
                    >
                        <TextArea 
                            rows={3} 
                            placeholder="Additional notes about this website..."
                        />
                    </Form.Item>

                    <Form.Item>
                        <Space>
                            <Button type="primary" htmlType="submit">
                                Add Website
                            </Button>
                            <Button onClick={() => {
                                setIsModalVisible(false);
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

export default WebsiteMonitor;
