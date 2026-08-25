import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getSale, paySale } from '../services/api';

const MONEY_FORMATTER = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
});

function formatMoney(value) {
  return MONEY_FORMATTER.format(Number(value) || 0);
}

export default function Payment() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const saleId = searchParams.get('sale_id');

  const [sale, setSale] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [paying, setPaying] = useState(false);
  const [paid, setPaid] = useState(false);
  const [method, setMethod] = useState('card');
  const [paymentError, setPaymentError] = useState('');

  // Card fields
  const [holderName, setHolderName] = useState('');
  const [panNumber, setPanNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [cvc, setCvc] = useState('');

  // UPI fields
  const [upiId, setUpiId] = useState('');
  const [upiValidated, setUpiValidated] = useState(false);

  // UPI IDs look like "yourname@upi" — validate before allowing payment.
  const upiValid = /^[\w.\-]{2,}@[a-zA-Z]{2,}$/.test(upiId.trim());
  const canPay = method === 'card' || (upiValid && upiValidated);

  useEffect(() => {
    if (!saleId) {
      navigate('/dashboard', { replace: true });
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const res = await getSale(saleId);
        if (cancelled) return;
        setSale(res.data);
        if (res.data.status === 'paid') setPaid(true);
      } catch (err) {
        if (cancelled) return;
        const status = err.response?.status;
        const detail = err.response?.data?.detail;
        if (status === 404) {
          setError('Order not found. It may have been removed or you may not have access.');
        } else {
          setError(typeof detail === 'string' ? detail : 'Failed to load the order. Please go back.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [saleId, navigate]);

  const handlePay = async (e) => {
    e.preventDefault();
    setPaymentError('');
    if (method === 'upi' && (!upiValid || !upiValidated)) {
      setPaymentError('Please enter a valid UPI ID and confirm it before paying.');
      return;
    }
    setPaying(true);
    try {
      const payload = {
        method,
        transaction_id: method === 'upi' && upiId ? upiId : null,
      };
      const res = await paySale(saleId, payload);
      setSale(res.data);
      setPaid(true);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setPaymentError(typeof detail === 'string' ? detail : 'Payment could not be completed. Please try again.');
    } finally {
      setPaying(false);
    }
  };

  // Live card-number formatting: 1234 5678 9012 3456
  const onPanChange = (e) => {
    const digits = e.target.value.replace(/\D/g, '').slice(0, 16);
    setPanNumber(digits.replace(/(.{4})/g, '$1 ').trim());
  };

  const onExpiryChange = (e) => {
    let v = e.target.value.replace(/\D/g, '').slice(0, 4);
    if (v.length >= 3) v = `${v.slice(0, 2)}/${v.slice(2)}`;
    setExpiry(v);
  };

  const goDashboard = () => navigate('/dashboard');

  return (
    <div className="payment-page">
      {/* Compact brand bar */}
      <header className="payment-brand-bar">
        <span className="brand-mark">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/>
            <line x1="3" y1="6" x2="21" y2="6"/>
            <path d="M16 10a4 4 0 0 1-8 0"/>
          </svg>
        </span>
        <span className="brand-lockup">
          <span className="brand-name">Ecommerce</span>
          <span className="brand-sub">Secure Checkout</span>
        </span>
        <button className="btn-back" onClick={goDashboard}>← Back to Dashboard</button>
      </header>

      {loading ? (
        <div className="payment-loading">
          <span className="spinner" />
          Loading your order…
        </div>
      ) : error ? (
        <div className="payment-error-card">
          <svg className="error-icon" xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          <h2>Unable to load order</h2>
          <p>{error}</p>
          <button className="btn-primary" onClick={goDashboard}>Back to Dashboard</button>
        </div>
      ) : paid ? (
        <div className="payment-success-card">
          <span className="success-check">
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 6 9 17l-5-5"/>
            </svg>
          </span>
          <h2>Payment Successful</h2>
          <p className="success-order-ref">Order {sale.id}</p>
          <p className="success-amount">Paid {formatMoney(sale.total_amount)}</p>
          <p className="success-meta">
            Your mock payment was processed securely. A receipt event was published to the Kafka sales topic.
          </p>
          <div className="success-actions">
            <button className="btn-primary" onClick={goDashboard}>Back to Dashboard</button>
            <button className="btn-ghost" onClick={goDashboard}>Continue Shopping</button>
          </div>
        </div>
      ) : (
        <div className="payment-layout">
          <section className="payment-form-card">
            <div className="payment-card-header">
              <h2>Complete your payment</h2>
              <p className="payment-intro">Order reference</p>
              <span className="order-ref">{sale.id}</span>
            </div>

            <div className="payment-tabs">
              <button className={`payment-tab ${method === 'card' ? 'is-active' : ''}`} onClick={() => setMethod('card')}>
                Card
              </button>
              <button className={`payment-tab ${method === 'upi' ? 'is-active' : ''}`} onClick={() => setMethod('upi')}>
                UPI
              </button>
            </div>

            {paymentError && <div className="payment-error-box">{paymentError}</div>}

            <form className="card-payment-form" onSubmit={handlePay}>
              {method === 'card' ? (
                <>
                  <div className="payment-row-2 card-grid">
                    <div className="form-group">
                      <label htmlFor="holderName">Name on card</label>
                      <input
                        id="holderName"
                        type="text"
                        autoComplete="cc-name"
                        placeholder="ANURAG KUMAR"
                        value={holderName}
                        onChange={(e) => setHolderName(e.target.value)}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label htmlFor="panNumber">Card number</label>
                      <input
                        id="panNumber"
                        type="text"
                        inputMode="numeric"
                        autoComplete="cc-number"
                        placeholder="1234 5678 9012 3456"
                        value={panNumber}
                        onChange={onPanChange}
                        maxLength={19}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label htmlFor="expiry">Expiry</label>
                      <input
                        id="expiry"
                        type="text"
                        inputMode="numeric"
                        autoComplete="cc-exp"
                        placeholder="MM/YY"
                        value={expiry}
                        onChange={onExpiryChange}
                        maxLength={5}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label htmlFor="cvc">CVC</label>
                      <input
                        id="cvc"
                        type="text"
                        inputMode="numeric"
                        autoComplete="cc-csc"
                        placeholder="123"
                        maxLength={3}
                        value={cvc}
                        onChange={(e) => setCvc(e.target.value.replace(/\D/g, '').slice(0, 3))}
                        required
                      />
                    </div>
                  </div>

                  {/* Live card preview */}
                  <div className="card-preview">
                    <div className="card-preview-brand">Ecommerce</div>
                    <div className="card-preview-nav">
                      <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="1" y="5" width="22" height="14" rx="2"/>
                        <line x1="1" y1="9" x2="23" y2="9"/>
                      </svg>
                    </div>
                    <div className="card-preview-number">{panNumber || '•••• •••• •••• 1234'}</div>
                    <div className="card-preview-meta">
                      <span>{holderName ? holderName.toUpperCase() : 'CARD HOLDER'}</span>
                      <span>{expiry || 'MM/YY'}</span>
                    </div>
                  </div>
                </>
              ) : (
                <div className="upi-box">
                  <div className="form-group">
                    <label htmlFor="upiId">UPI ID</label>
                    <input
                      id="upiId"
                      type="text"
                      autoComplete="username"
                      placeholder="yourname@upi"
                      value={upiId}
                      onChange={(e) => setUpiId(e.target.value)}
                      required
                    />
                  </div>
                  <p className="upi-hint">
                    Enter your UPI ID to receive a mock payment request on any UPI app.
                  </p>

                  <label className={`upi-validate ${upiValidated ? 'is-validated' : ''}`}>
                    <input
                      type="checkbox"
                      checked={upiValidated}
                      onChange={(e) => setUpiValidated(e.target.checked)}
                    />
                    <span className="upi-validate-text">
                      I confirm my UPI ID{upiId ? <strong> {upiId}</strong> : ''} is correct and I
                      authorize this payment.
                    </span>
                  </label>
                  {upiId && !upiValid && (
                    <p className="upi-error">
                      Please enter a valid UPI ID (for example: yourname@upi).
                    </p>
                  )}
                </div>
              )}

              <button className="btn-pay btn-primary" disabled={paying || !canPay}>
                {paying ? (
                  <span className="btn-spinner-row">
                    <span className="spinner spinner-light" />
                    Processing…
                  </span>
                ) : (
                  `Pay ${formatMoney(sale.total_amount)}`
                )}
              </button>
              <p className="secure-note">
                <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="11" width="18" height="11" rx="2"/>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
                Secured with mock encryption · {method === 'upi' ? 'UPI' : 'Card'} payments
              </p>
            </form>

          </section>

          {/* Right — order summary */}
          <aside className="order-summary-card">
            <div className="order-summary-header">
              <h3>Order Summary</h3>
              <span className={`sale-status-chip ${sale.status}`}>
                <span className="status-dot" />
                {sale.status}
              </span>
            </div>
            <div className="order-ref-row">
              <span>Order ref</span>
              <strong>{sale.id}</strong>
            </div>
            <div className="order-items">
              {sale.items.map((item) => (
                <div className="order-item" key={item.id}>
                  <div className="order-item-info">
                    <span className="order-item-name">
                      {item.product_name || 'Product'}
                    </span>
                    <span className="order-item-qty">Qty {item.quantity}</span>
                  </div>
                  <span className="order-item-line-total">{formatMoney(item.line_total)}</span>
                </div>
              ))}
            </div>
            <div className="order-sums">
              <div className="order-sum-row"><span>Subtotal</span><strong>{formatMoney(sale.subtotal)}</strong></div>
              <div className="order-sum-row"><span>Tax (12.5%)</span><strong>{formatMoney(sale.tax_amount)}</strong></div>
              <div className="order-sum-row"><span>Discount</span><strong>- {formatMoney(sale.discount_amount)}</strong></div>
              <div className="order-sum-row order-total-row"><span>Total</span><strong>{formatMoney(sale.total_amount)}</strong></div>
            </div>
            <div className="order-pay-note">
              By clicking Pay you agree to the <a href="#">Terms of Service</a>.
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}