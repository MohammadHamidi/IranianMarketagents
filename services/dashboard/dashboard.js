import React, { useState, useEffect } from 'react';
import { Search, TrendingUp, TrendingDown, AlertTriangle, DollarSign, Eye, Filter, Calendar } from 'lucide-react';

const IranianPriceDashboard = () => {
  const [products, setProducts] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [priceHistory, setPriceHistory] = useState([]);
  const [exchangeRate, setExchangeRate] = useState(null);
  const [marketTrends, setMarketTrends] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);

  // Mock data - in production this would come from your API
  const mockExchangeRate = {
    usd_to_irr: 425000,
    eur_to_irr: 470000,
    updated_at: new Date().toISOString()
  };

  const mockProducts = [
    {
      product_id: 'samsung_galaxy_s21_128gb',
      canonical_title: 'Samsung Galaxy S21 128GB',
      canonical_title_fa: 'سامسونگ گلکسی اس ۲۱ ۱۲۸ گیگابایت',
      brand: 'Samsung',
      category: 'mobile',
      current_prices: [
        {
          vendor: 'digikala',
          vendor_name_fa: 'دیجی‌کالا',
          price_toman: 25000000,
          price_usd: 588,
          availability: true,
          product_url: 'https://digikala.com/product/samsung-s21',
          last_updated: new Date()
        },
        {
          vendor: 'technolife',
          vendor_name_fa: 'تکنولایف',
          price_toman: 24800000,
          price_usd: 583,
          availability: true,
          product_url: 'https://technolife.ir/samsung-s21',
          last_updated: new Date()
        }
      ],
      lowest_price: { vendor: 'technolife', price_toman: 24800000, price_usd: 583 },
      highest_price: { vendor: 'digikala', price_toman: 25000000, price_usd: 588 },
      price_range_pct: 0.8,
      available_vendors: 2
    },
    {
      product_id: 'iphone_13_128gb',
      canonical_title: 'iPhone 13 128GB',
      canonical_title_fa: 'آیفون ۱۳ - ۱۲۸ گیگابایت',
      brand: 'Apple',
      category: 'mobile',
      current_prices: [
        {
          vendor: 'digikala',
          vendor_name_fa: 'دیجی‌کالا',
          price_toman: 35000000,
          price_usd: 824,
          availability: true,
          product_url: 'https://digikala.com/product/iphone-13',
          last_updated: new Date()
        }
      ],
      lowest_price: { vendor: 'digikala', price_toman: 35000000, price_usd: 824 },
      highest_price: { vendor: 'digikala', price_toman: 35000000, price_usd: 824 },
      price_range_pct: 0,
      available_vendors: 1
    }
  ];

  const mockTrends = [
    {
      category: 'mobile',
      avg_price_change_24h: -2.3,
      avg_price_change_7d: -5.1,
      avg_price_change_30d: 12.4,
      total_products: 157
    },
    {
      category: 'laptop',
      avg_price_change_24h: 1.2,
      avg_price_change_7d: 3.8,
      avg_price_change_30d: 18.2,
      total_products: 89
    }
  ];

  useEffect(() => {
    // Simulate API calls
    setExchangeRate(mockExchangeRate);
    setProducts(mockProducts);
    setMarketTrends(mockTrends);
  }, []);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    
    setLoading(true);
    
    // Simulate API call
    setTimeout(() => {
      const filtered = mockProducts.filter(p => 
        p.canonical_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.canonical_title_fa.includes(searchQuery)
      );
      setProducts(filtered);
      setLoading(false);
    }, 1000);
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('fa-IR').format(price);
  };

  const formatPriceChangeColor = (change) => {
    if (change > 0) return 'text-red-600';
    if (change < 0) return 'text-green-600';
    return 'text-gray-600';
  };

  const TrendIcon = ({ change }) => {
    if (change > 0) return <TrendingUp className="w-4 h-4 text-red-600" />;
    if (change < 0) return <TrendingDown className="w-4 h-4 text-green-600" />;
    return <div className="w-4 h-4" />;
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6" dir="rtl">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">
          پلتفرم هوش قیمت ایران
        </h1>
        <p className="text-gray-600">
          اطلاعات قیمت لحظه‌ای از فروشگاه‌های بزرگ ایران
        </p>
        
        {/* Exchange Rate Display */}
        {exchangeRate && (
          <div className="mt-4 flex items-center space-x-6 space-x-reverse">
            <div className="flex items-center">
              <DollarSign className="w-5 h-5 text-green-600 ml-2" />
              <span className="text-sm font-medium">
                نرخ دلار: {formatPrice(exchangeRate.usd_to_irr)} ریال
              </span>
            </div>
            <div className="flex items-center">
              <Calendar className="w-5 h-5 text-blue-600 ml-2" />
              <span className="text-sm text-gray-600">
                آخرین به‌روزرسانی: {new Date(exchangeRate.updated_at).toLocaleString('fa-IR')}
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Sidebar - Search & Filters */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center">
              <Filter className="w-5 h-5 ml-2" />
              جست‌وجو و فیلتر
            </h3>
            
            {/* Search */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                جست‌وجوی محصول
              </label>
              <div className="relative">
                <input
                  type="text"
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="نام محصول را وارد کنید..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                />
                <button
                  onClick={handleSearch}
                  className="absolute left-2 top-2 p-1 text-gray-400 hover:text-gray-600"
                >
                  <Search className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Category Filter */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                دسته‌بندی
              </label>
              <select
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
              >
                <option value="all">همه محصولات</option>
                <option value="mobile">گوشی موبایل</option>
                <option value="laptop">لپ تاپ</option>
                <option value="tablet">تبلت</option>
                <option value="headphones">هدفون</option>
              </select>
            </div>

            {/* Market Trends */}
            <div className="mt-6">
              <h4 className="font-semibold mb-3">روند بازار</h4>
              {marketTrends.map((trend, index) => (
                <div key={index} className="mb-3 p-3 bg-gray-50 rounded-md">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium">
                      {trend.category === 'mobile' ? 'موبایل' : 'لپ تاپ'}
                    </span>
                    <span className="text-sm text-gray-600">
                      {trend.total_products} محصول
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center">
                      <TrendIcon change={trend.avg_price_change_24h} />
                      <span className={`mr-1 ${formatPriceChangeColor(trend.avg_price_change_24h)}`}>
                        {trend.avg_price_change_24h > 0 ? '+' : ''}{trend.avg_price_change_24h.toFixed(1)}%
                      </span>
                    </div>
                    <span className="text-gray-500">24 ساعت</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Main Content - Product List */}
        <div className="lg:col-span-3">
          <div className="bg-white rounded-lg shadow-md">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold flex items-center">
                <Eye className="w-5 h-5 ml-2" />
                نتایج جست‌وجو ({products.length} محصول)
              </h3>
            </div>

            {loading ? (
              <div className="p-6 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-2 text-gray-600">در حال جست‌وجو...</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {products.map((product) => (
                  <div key={product.product_id} className="p-6 hover:bg-gray-50">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h4 className="text-lg font-semibold text-gray-800 mb-1">
                          {product.canonical_title_fa}
                        </h4>
                        <p className="text-sm text-gray-600 mb-3">
                          {product.canonical_title} • برند: {product.brand}
                        </p>

                        {/* Price Comparison */}
                        <div className="space-y-2">
                          {product.current_prices.map((price, index) => (
                            <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
                              <div className="flex items-center">
                                <div className="w-3 h-3 bg-blue-600 rounded-full ml-3"></div>
                                <div>
                                  <span className="font-medium">{price.vendor_name_fa}</span>
                                  {price.availability ? (
                                    <span className="mr-2 px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                                      موجود
                                    </span>
                                  ) : (
                                    <span className="mr-2 px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full">
                                      ناموجود
                                    </span>
                                  )}
                                </div>
                              </div>
                              <div className="text-left">
                                <div className="font-bold text-lg">
                                  {formatPrice(price.price_toman)} تومان
                                </div>
                                <div className="text-sm text-gray-600">
                                  ≈ ${price.price_usd}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>

                        {/* Price Range Info */}
                        {product.price_range_pct > 0 && (
                          <div className="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded-md">
                            <div className="flex items-center">
                              <AlertTriangle className="w-4 h-4 text-yellow-600 ml-2" />
                              <span className="text-sm text-yellow-800">
                                اختلاف قیمت بین فروشگاه‌ها: {product.price_range_pct.toFixed(1)}%
                              </span>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Best Price Badge */}
                      <div className="mr-4 text-center">
                        <div className="bg-green-100 text-green-800 px-3 py-2 rounded-lg">
                          <div className="text-xs">بهترین قیمت</div>
                          <div className="font-bold">
                            {formatPrice(product.lowest_price.price_toman)}
                          </div>
                          <div className="text-xs">
                            {product.current_prices.find(p => p.price_toman === product.lowest_price.price_toman)?.vendor_name_fa}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="mt-4 flex space-x-3 space-x-reverse">
                      <button
                        onClick={() => setSelectedProduct(product)}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                      >
                        مشاهده تاریخچه قیمت
                      </button>
                      <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors">
                        تنظیم هشدار قیمت
                      </button>
                      {product.current_prices.map((price) => (
                        <a
                          key={price.vendor}
                          href={price.product_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                        >
                          خرید از {price.vendor_name_fa}
                        </a>
                      ))}
                    </div>
                  </div>
                ))}

                {products.length === 0 && !loading && (
                  <div className="p-6 text-center text-gray-500">
                    محصولی یافت نشد. لطفاً کلمات کلیدی دیگری امتحان کنید.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Price History Modal */}
      {selectedProduct && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200 flex justify-between items-center">
              <h3 className="text-xl font-semibold">
                تاریخچه قیمت: {selectedProduct.canonical_title_fa}
              </h3>
              <button
                onClick={() => setSelectedProduct(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            
            <div className="p-6">
              {/* Placeholder for price chart */}
              <div className="bg-gray-100 h-64 rounded-lg flex items-center justify-center mb-6">
                <p className="text-gray-600">نمودار تاریخچه قیمت (قابل پیاده‌سازی با Chart.js یا Recharts)</p>
              </div>
              
              {/* Current price summary */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg text-center">
                  <div className="text-blue-600 font-semibold">قیمت فعلی (کمترین)</div>
                  <div className="text-2xl font-bold">{formatPrice(selectedProduct.lowest_price.price_toman)} تومان</div>
                </div>
                <div className="bg-green-50 p-4 rounded-lg text-center">
                  <div className="text-green-600 font-semibold">تعداد فروشگاه‌ها</div>
                  <div className="text-2xl font-bold">{selectedProduct.available_vendors} فروشگاه</div>
                </div>
                <div className="bg-yellow-50 p-4 rounded-lg text-center">
                  <div className="text-yellow-600 font-semibold">محدوده قیمت</div>
                  <div className="text-2xl font-bold">{selectedProduct.price_range_pct.toFixed(1)}%</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IranianPriceDashboard;