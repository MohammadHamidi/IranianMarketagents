import React from 'react';
import { Card, Form, Input, Button, Switch, Select, Divider } from 'antd';

const Settings = () => {
    const [form] = Form.useForm();

    const onFinish = (values) => {
        console.log('Settings updated:', values);
    };

    return (
        <div>
            <h1>Settings</h1>

            <Card title="Platform Configuration">
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={onFinish}
                    initialValues={{
                        platformName: 'Iranian Price Intelligence Platform',
                        timezone: 'Asia/Tehran',
                        language: 'fa',
                        enableNotifications: true,
                        enableAutoScraping: true,
                    }}
                >
                    <Form.Item
                        label="Platform Name"
                        name="platformName"
                        rules={[{ required: true, message: 'Please input platform name!' }]}
                    >
                        <Input />
                    </Form.Item>

                    <Form.Item
                        label="Timezone"
                        name="timezone"
                        rules={[{ required: true, message: 'Please select timezone!' }]}
                    >
                        <Select>
                            <Select.Option value="Asia/Tehran">Asia/Tehran (IRST)</Select.Option>
                            <Select.Option value="UTC">UTC</Select.Option>
                        </Select>
                    </Form.Item>

                    <Form.Item
                        label="Language"
                        name="language"
                        rules={[{ required: true, message: 'Please select language!' }]}
                    >
                        <Select>
                            <Select.Option value="fa">فارسی (Persian)</Select.Option>
                            <Select.Option value="en">English</Select.Option>
                        </Select>
                    </Form.Item>

                    <Divider />

                    <Form.Item
                        label="Enable Notifications"
                        name="enableNotifications"
                        valuePropName="checked"
                    >
                        <Switch />
                    </Form.Item>

                    <Form.Item
                        label="Enable Auto Scraping"
                        name="enableAutoScraping"
                        valuePropName="checked"
                    >
                        <Switch />
                    </Form.Item>

                    <Form.Item>
                        <Button type="primary" htmlType="submit">
                            Save Settings
                        </Button>
                    </Form.Item>
                </Form>
            </Card>
        </div>
    );
};

export default Settings;
