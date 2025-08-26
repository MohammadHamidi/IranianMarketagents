import React from 'react';
import { Card, Table, Input, Button, Space, Tag } from 'antd';
import { SearchOutlined, PlusOutlined } from '@ant-design/icons';

const Products = () => {
    const products = [
        {
            key: '1',
            id: 'PROD001',
            name: 'Samsung Galaxy S21',
            nameFa: 'سامسونگ گلکسی اس ۲۱',
            category: 'Mobile',
            vendor: 'Digikala',
            price: '25,000,000 تومان',
            status: 'active',
        },
        {
            key: '2',
            id: 'PROD002',
            name: 'iPhone 13 Pro',
            nameFa: 'آیفون ۱۳ پرو',
            category: 'Mobile',
            vendor: 'Snap',
            price: '32,500,000 تومان',
            status: 'active',
        },
    ];

    const columns = [
        {
            title: 'Product ID',
            dataIndex: 'id',
            key: 'id',
        },
        {
            title: 'Product Name',
            dataIndex: 'name',
            key: 'name',
            render: (text, record) => (
                <div>
                    <div>{text}</div>
                    <div style={{ fontSize: '12px', color: '#666' }}>{record.nameFa}</div>
                </div>
            ),
        },
        {
            title: 'Category',
            dataIndex: 'category',
            key: 'category',
        },
        {
            title: 'Vendor',
            dataIndex: 'vendor',
            key: 'vendor',
        },
        {
            title: 'Price',
            dataIndex: 'price',
            key: 'price',
        },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            render: (status) => (
                <Tag color={status === 'active' ? 'green' : 'red'}>
                    {status.toUpperCase()}
                </Tag>
            ),
        },
    ];

    return (
        <div>
            <Card title="Products Management">
                <Space style={{ marginBottom: 16 }}>
                    <Input
                        placeholder="Search products..."
                        prefix={<SearchOutlined />}
                        style={{ width: 300 }}
                    />
                    <Button type="primary" icon={<PlusOutlined />}>
                        Add Product
                    </Button>
                </Space>

                <Table
                    columns={columns}
                    dataSource={products}
                    pagination={{ pageSize: 10 }}
                />
            </Card>
        </div>
    );
};

export default Products;
