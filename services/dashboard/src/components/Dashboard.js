import React from 'react';
import { Card, Row, Col, Statistic, Table, Tag } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

const Dashboard = () => {
  const stats = [
    { title: 'Total Products', value: 15420, prefix: '📦' },
    { title: 'Active Vendors', value: 8, prefix: '🏪' },
    { title: 'Price Changes Today', value: 342, prefix: '📈' },
    { title: 'New Products', value: 156, prefix: '🆕' },
  ];

  const recentProducts = [
    {
      key: '1',
      name: 'Samsung Galaxy S21',
      nameFa: 'سامسونگ گلکسی اس ۲۱',
      vendor: 'Digikala',
      price: '25,000,000 تومان',
      change: '+5.2%',
      changeType: 'up',
    },
    {
      key: '2',
      name: 'iPhone 13 Pro',
      nameFa: 'آیفون ۱۳ پرو',
      vendor: 'Snap',
      price: '32,500,000 تومان',
      change: '-2.1%',
      changeType: 'down',
    },
  ];

  const columns = [
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
      title: 'Change',
      dataIndex: 'change',
      key: 'change',
      render: (text, record) => (
        <Tag color={record.changeType === 'up' ? 'green' : 'red'}>
          {record.changeType === 'up' ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
          {text}
        </Tag>
      ),
    },
  ];

  return (
    <div>
      <h1>Dashboard</h1>
      
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
          <Card title="Recent Price Changes" style={{ marginBottom: '24px' }}>
            <Table
              columns={columns}
              dataSource={recentProducts}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
