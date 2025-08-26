import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import Dashboard from './components/Dashboard';
import Products from './components/Products';
import Analytics from './components/Analytics';
import Settings from './components/Settings';
import './App.css';

const { Header, Content, Footer } = Layout;

function App() {
  const menuItems = [
    { key: 'dashboard', label: 'Dashboard' },
    { key: 'products', label: 'Products' },
    { key: 'analytics', label: 'Analytics' },
    { key: 'settings', label: 'Settings' },
  ];

  return (
    <Router>
      <Layout className="layout" style={{ minHeight: '100vh' }}>
        <Header style={{ background: '#001529' }}>
          <div style={{ color: 'white', fontSize: '20px', fontWeight: 'bold' }}>
            🇮🇷 Iranian Price Intelligence
          </div>
          <Menu
            theme="dark"
            mode="horizontal"
            defaultSelectedKeys={['dashboard']}
            items={menuItems}
            style={{ background: 'transparent', border: 'none' }}
          />
        </Header>
        
        <Content style={{ padding: '24px', background: '#f0f2f5' }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/products" element={<Products />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Content>
        
        <Footer style={{ textAlign: 'center', background: '#f0f2f5' }}>
          Iranian Price Intelligence Platform ©2025
        </Footer>
      </Layout>
    </Router>
  );
}

export default App;
