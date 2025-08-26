import React from 'react';
import { Card, Row, Col, Statistic } from 'antd';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const Analytics = () => {
    const priceData = [
        { date: '2025-01-01', price: 25000000 },
        { date: '2025-01-02', price: 24800000 },
        { date: '2025-01-03', price: 25200000 },
        { date: '2025-01-04', price: 25500000 },
        { date: '2025-01-05', price: 25300000 },
        { date: '2025-01-06', price: 25600000 },
        { date: '2025-01-07', price: 25800000 },
    ];

    const stats = [
        { title: 'Average Price', value: '25,400,000 تومان', prefix: '💰' },
        { title: 'Price Volatility', value: '2.3%', prefix: '📊' },
        { title: 'Trend Direction', value: 'Upward', prefix: '📈' },
        { title: 'Market Share', value: '15.2%', prefix: '🎯' },
    ];

    return (
        <div>
            <h1>Analytics</h1>

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
        </div>
    );
};

export default Analytics;
