import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createProduct, getKafkaStatus, getProducts } from '../services/api';

const WS_BASE = `ws://${window.location.hostname}:8000/api/v1/ws/kafka/events`;

function generateId() {
  try {
    return crypto.randomUUID();
  } catch {
    return Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
  }
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [isLight, setIsLight] = useState(() => {
    try { return localStorage.getItem('theme') === 'light'; } catch { return false; }
  });

  useEffect(() => {
    document.documentElement.classList.toggle('light-theme', isLight);
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
  }, [isLight]);
  const [loading, setLoading] = useState(true);
  const [kafkaStatus, setKafkaStatus] = useState(null);
  const [connected, setConnected] = useState(false);
  const [filter, setFilter] = useState('all');
  const [showForm, setShowForm] = useState(false);
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Product form state
  const [sku, setSku] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [price, setPrice] = useState('');
  const [stockQuantity, setStockQuantity] = useState('');

  const successTimer = useRef(null);
  const errorTimer = useRef(null);
  const [expandedDesc, setExpandedDesc] = useState(new Set());

  // Fetch existing products and Kafka status on mount
  useEffect(() => {
    setLoading(true);
    Promise.all([
      getProducts().then((res) => setProducts(res.data)).catch(() => setProducts([])),
      getKafkaStatus().then((res) => setKafkaStatus(res.data)).catch(() => setKafkaStatus({ enabled: false, started: false })),
    ]).finally(() => setLoading(false));
  }, []);

  // Connect WebSocket for real-time events
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/login');
      return;
    }

    const ws = new WebSocket(`${WS_BASE}?token=${token}`);

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        if (data.error) return;

        const topic = data.topic || '';
        const isProductEvent = topic.includes('product');
        if (!isProductEvent) return;

        const value = data.value || {};
        const payload = value.payload || value;
        if (payload && payload.id) {
          setProducts((prev) => {
            // Avoid duplicates
            if (prev.some((p) => p.id === payload.id)) return prev;
            return [payload, ...prev];
          });
        }
      } catch {
        // ignore
      }
    };

    return () => ws.close();
  }, [navigate]);

  // Cleanup timers
  useEffect(() => {
    return () => {
      if (successTimer.current) clearTimeout(successTimer.current);
      if (errorTimer.current) clearTimeout(errorTimer.current);
    };
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  const handleCreateProduct = async (e) => {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');
    setSubmitting(true);

    try {
      const res = await createProduct({
        sku,
        name,
        description: description || undefined,
        price: parseFloat(price),
        stock_quantity: parseInt(stockQuantity, 10),
      });

      // Add the created product to the list immediately
      const newProduct = res.data;
      setProducts((prev) => [newProduct, ...prev]);

      setFormSuccess(`Product "${name}" created successfully!`);
      setSku('');
      setName('');
      setDescription('');
      setPrice('');
      setStockQuantity('');
      setShowForm(false);

      if (successTimer.current) clearTimeout(successTimer.current);
      successTimer.current = setTimeout(() => setFormSuccess(''), 4000);
    } catch (err) {
      const detail = err.response?.data?.detail || 'Failed to create product.';
      setFormError(typeof detail === 'string' ? detail : JSON.stringify(detail));
      if (errorTimer.current) clearTimeout(errorTimer.current);
      errorTimer.current = setTimeout(() => setFormError(''), 6000);
    } finally {
      setSubmitting(false);
    }
  };

  const filteredProducts =
    filter === 'all'
      ? products
      : filter === 'products'
        ? products
        : [];

  const toggleDescription = (productId) => {
    setExpandedDesc((prev) => {
      const next = new Set(prev);
      if (next.has(productId)) {
        next.delete(productId);
      } else {
        next.add(productId);
      }
      return next;
    });
  };
  return (
    <div className="dashboard">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-left">
          <h1>Ecommerce Dashboard</h1>
          <span className={`status-indicator ${connected ? 'connected' : 'disconnected'}`}>
            {connected ? '● Live' : '○ Offline'}
          </span>
        </div>
        <div className="header-right">
          <span className="user-info">{(() => { try { const u = JSON.parse(localStorage.getItem('user') || '{}'); return u.full_name || u.email?.split('@')[0] || 'User'; } catch { return 'User'; } })()}</span>
          <button className="btn-theme" onClick={() => setIsLight((prev) => !prev)} title={isLight ? 'Switch to dark mode' : 'Switch to light mode'}>
            {isLight ? '🌙' : '☀️'}
          </button>
          <button className="btn-logout" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      {/* Status Bar */}
      <div className="status-bar">
        <span className="status-item">Products</span>
        <span className="status-separator">|</span>
        <span className="status-item">Real-time: {connected ? 'Connected' : 'Offline'}</span>
        <span className="status-separator">|</span>
        <span className="event-badge">{filteredProducts.length} products</span>
      </div>

      {/* Action Bar */}
      <div className="action-bar">
        <button className="btn-action" onClick={() => setShowForm(!showForm)}>
          {showForm ? '− Cancel' : '+ New Product'}
        </button>
      </div>

      {/* Toast notifications */}
      {formSuccess && <div className="toast toast-success">{formSuccess}</div>}
      {formError && <div className="toast toast-error">{formError}</div>}

      {/* Create Product Form */}
      {/* Create Product Modal */}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowForm(false)}>
              ×
            </button>
            <h3>Create Product</h3>
            <form onSubmit={handleCreateProduct}>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="sku">SKU *</label>
                  <input
                    id="sku"
                    type="text"
                    value={sku}
                    onChange={(e) => setSku(e.target.value)}
                    placeholder="PROD-001"
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="pname">Name *</label>
                  <input
                    id="pname"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Product Name"
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="desc">Description</label>
                <textarea
                  id="desc"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Product description (optional)"
                  rows={2}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="price">Price *</label>
                  <input
                    id="price"
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    placeholder="29.99"
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="stock">Stock Quantity *</label>
                  <input
                    id="stock"
                    type="number"
                    step="1"
                    min="0"
                    value={stockQuantity}
                    onChange={(e) => setStockQuantity(e.target.value)}
                    placeholder="100"
                    required
                  />
                </div>
              </div>

              <button type="submit" className="btn-primary" disabled={submitting}>
                {submitting ? 'Creating...' : 'Create Product'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Product List */}
      <div className="event-list">
        {loading ? (
          <div className="empty-state"><p>Loading products...</p></div>
        ) : filteredProducts.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📦</div>
            <p>No products yet.</p>
            <p>Click "+ New Product" above to create your first product.</p>
          </div>
        ) : (
          filteredProducts.map((product) => (
            <div key={product.id} className="product-card">
              <div className="product-card-header">
                <span className="product-name">{product.name || 'Unknown Product'}</span>
                <span className="event-time">
                  {product.created_at ? new Date(product.created_at).toLocaleDateString('en-IN') : ''}
                </span>
              </div>
              <div className="product-card-body">
                <div className="product-detail">
                  <span className="detail-label">SKU</span>
                  <span className="detail-value">{product.sku || '-'}</span>
                </div>
                <div className="product-detail">
                  <span className="detail-label">Price</span>
                  <span className="detail-value price">₹{Math.round(product.price) || 0}</span>
                </div>
                <div className="product-detail">
                  <span className="detail-label">Stock</span>
                  <span className="detail-value">{product.stock_quantity ?? '-'}</span>
                </div>
                <div className="product-detail">
                  <span className="detail-label">Status</span>
                  <span className={`detail-value ${product.is_active ? 'active' : 'inactive'}`}>
                    {product.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                {product.description && (
                  <div className="product-detail description">
                    <span className="detail-label">Description</span>
                    <span className="detail-value">
                      {expandedDesc.has(product.id)
                        ? product.description
                        : product.description.split(' ').slice(0, 2).join(' ')
                      }
                      {!expandedDesc.has(product.id) && product.description.split(' ').length > 2 && (
                        <span className="more-link" onClick={() => toggleDescription(product.id)}>...more</span>
                      )}
                      {expandedDesc.has(product.id) && product.description.split(' ').length > 2 && (
                        <span className="more-link" onClick={() => toggleDescription(product.id)}> less</span>
                      )}                    
                    </span>
                  </div>
                )}
              </div>
              <div className="product-card-footer">
                <span className="event-type-badge">ID: {product.id?.substring(0, 8)}...</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}