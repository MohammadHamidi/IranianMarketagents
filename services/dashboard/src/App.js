import React, { useState } from 'react';
import { Layout, Menu, Typography, Space, Badge, Avatar } from 'antd';
import {
  DashboardOutlined,
  SearchOutlined,
  BarChartOutlined,
  SettingOutlined,
  BellOutlined,
  UserOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import './App.css';

// Import components
import Dashboard from './components/Dashboard';
import Products from './components/Products';
import Analytics from './components/Analytics';
import Settings from './components/Settings';
import WebsiteMonitor from './components/WebsiteMonitor';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

function App() {
  const [selectedKey, setSelectedKey] = useState('dashboard');
  const [collapsed, setCollapsed] = useState(false);

  const menuItems = [
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: 'داشبورد',
    },
    {
      key: 'products',
      icon: <SearchOutlined />,
      label: 'محصولات',
    },
    {
      key: 'websites',
      icon: <GlobalOutlined />,
      label: 'مانیتورینگ سایت‌ها',
    },
    {
      key: 'analytics',
      icon: <BarChartOutlined />,
      label: 'تحلیل‌ها',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'تنظیمات',
    },
  ];

  const renderContent = () => {
    switch (selectedKey) {
      case 'dashboard':
        return <Dashboard />;
      case 'products':
        return <Products />;
      case 'websites':
        return <WebsiteMonitor />;
      case 'analytics':
        return <Analytics />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <Layout style={{ minHeight: '100vh', direction: 'rtl' }}>
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed}
        style={{
          background: '#001529',
        }}
      >
        <div style={{ 
          height: 64, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          color: 'white',
          fontSize: collapsed ? '16px' : '18px',
          fontWeight: 'bold'
        }}>
          {collapsed ? '🇮🇷' : '🇮🇷 سامانه هوش قیمت'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => setSelectedKey(key)}
        />
      </Sider>
      
      <Layout>
        <Header style={{ 
          padding: '0 24px', 
          background: '#fff', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
        }}>
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              {selectedKey === 'dashboard' && 'داشبورد'}
              {selectedKey === 'products' && 'محصولات'}
              {selectedKey === 'websites' && 'مانیتورینگ سایت‌ها'}
              {selectedKey === 'analytics' && 'تحلیل‌ها'}
              {selectedKey === 'settings' && 'تنظیمات'}
            </Title>
          </Space>
          
          <Space size="large">
            <Badge count={5}>
              <BellOutlined style={{ fontSize: '18px', cursor: 'pointer' }} />
            </Badge>
            <Avatar icon={<UserOutlined />} />
          </Space>
        </Header>
        
        <Content style={{ 
          margin: '24px', 
          padding: '24px', 
          background: '#fff', 
          borderRadius: '8px',
          minHeight: 'calc(100vh - 112px)'
        }}>
          {renderContent()}
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;
