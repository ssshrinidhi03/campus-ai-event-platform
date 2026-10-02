import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './LoginPage.css';

const DEMO_ACCOUNTS = [
  { label: 'Student', email: 'student@campus.edu', password: 'demo123' },
  { label: 'Organizer', email: 'organizer@campus.edu', password: 'demo123' },
  { label: 'Admin', email: 'admin@campus.edu', password: 'demo123' },
];

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await login(form.email, form.password);
      const role = data.user.role;
      if (role === 'ORGANIZER') navigate('/organizer');
      else if (role === 'ADMIN') navigate('/admin');
      else navigate('/events');
    } catch (err) {
      setError(err.message || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  function fillDemo(acc) {
    setForm({ email: acc.email, password: acc.password });
    setError('');
  }

  return (
    <div className="login-page">
      {/* Background blobs */}
      <div className="bg-blob blob-1" />
      <div className="bg-blob blob-2" />

      <div className="login-box card-glass animate-fade-in">
        {/* Header */}
        <div className="login-header">
          <span className="login-logo-icon">⚡</span>
          <h1 className="login-title font-display">
            Campus<span className="gradient-text">AI</span> Events
          </h1>
          <p className="text-secondary text-sm">
            Discover AI-powered campus events
          </p>
        </div>

        {/* Demo buttons */}
        <div className="demo-accounts">
          <p className="text-xs text-muted" style={{ marginBottom: '0.5rem' }}>Quick demo sign-in:</p>
          <div className="demo-btns">
            {DEMO_ACCOUNTS.map(acc => (
              <button key={acc.label} className="demo-btn" onClick={() => fillDemo(acc)}>
                {acc.label}
              </button>
            ))}
          </div>
        </div>

        {/* Form */}
        <form className="login-form" onSubmit={handleSubmit} id="login-form">
          <div className="field-group">
            <label className="field-label" htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              className="input"
              placeholder="you@campus.edu"
              value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              required
              autoComplete="email"
            />
          </div>

          <div className="field-group">
            <label className="field-label" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              className="input"
              placeholder="••••••••"
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              required
              autoComplete="current-password"
            />
          </div>

          {error && (
            <div className="login-error" role="alert">{error}</div>
          )}

          <button
            id="login-submit-btn"
            type="submit"
            className="btn btn-primary w-full"
            disabled={loading}
            style={{ marginTop: '0.5rem', height: '2.75rem', fontSize: '0.95rem' }}
          >
            {loading ? (
              <span className="spinner" />
            ) : (
              'Sign in →'
            )}
          </button>
        </form>

        <p className="login-footer text-xs text-muted">
          Authentication is implemented in Phase 3.
          Use the demo accounts above to explore the platform.
        </p>
      </div>
    </div>
  );
}
