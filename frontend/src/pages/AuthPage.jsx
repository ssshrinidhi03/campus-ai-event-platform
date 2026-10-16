import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../services/api';
import './AuthPage.css';

export default function AuthPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState('login');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Login form state
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });

  // Sign up form state
  const [signupForm, setSignupForm] = useState({
    name: '',
    roll_number: '',
    email: '',
    password: '',
    confirm_password: '',
  });

  async function handleLogin(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await login(loginForm.email, loginForm.password);
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

  async function handleSignup(e) {
    e.preventDefault();
    setError('');

    // Client-side validation
    if (!signupForm.name.trim()) {
      setError('Full name is required');
      return;
    }
    if (!signupForm.roll_number.trim()) {
      setError('College roll number is required');
      return;
    }
    if (!signupForm.email.trim()) {
      setError('Email address is required');
      return;
    }
    if (!signupForm.password) {
      setError('Password is required');
      return;
    }
    if (signupForm.password !== signupForm.confirm_password) {
      setError('Passwords do not match');
      return;
    }
    if (signupForm.password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);
    try {
      const data = await authApi.register(
        signupForm.name.trim(),
        signupForm.email.trim(),
        signupForm.password,
        signupForm.roll_number.trim().toUpperCase()
      );
      // Store the registration token and user so the account is recognized
      // as authenticated (but unverified) until email verification completes.
      localStorage.setItem('caep_token', data.access_token);
      localStorage.setItem('caep_user', JSON.stringify(data.user));
      setError('Registration successful! Please check your email to verify your account.');
      navigate('/verify-email');
    } catch (err) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  function fillDemo(acc) {
    setLoginForm({ email: acc.email, password: acc.password });
    setError('');
    setActiveTab('login');
  }

  const DEMO_ACCOUNTS = [
    { label: 'Student', email: 'student@campus.edu', password: 'student123' },
    { label: 'AI Club', email: 'aiclub@campus.edu', password: 'aiclub123' },
    { label: 'Coding Club', email: 'codingclub@campus.edu', password: 'codingclub123' },
    { label: 'E-Cell', email: 'ecell@campus.edu', password: 'ecell123' },
    { label: 'Photography Club', email: 'photoclub@campus.edu', password: 'photoclub123' },
  ];

  return (
    <div className="auth-page">
      {/* Background blobs */}
      <div className="bg-blob blob-1" />
      <div className="bg-blob blob-2" />

      <div className="auth-box card-glass animate-fade-in">
        {/* Header */}
        <div className="auth-header">
          <span className="auth-logo-icon">⚡</span>
          <h1 className="auth-title font-display">
            Campus<span className="gradient-text">AI</span> Events
          </h1>
          <p className="text-secondary text-sm">
            Discover AI-powered campus events
          </p>
        </div>

        {/* Tabs */}
        <div className="auth-tabs" role="tablist">
          <button
            role="tab"
            aria-selected={activeTab === 'login'}
            className={`auth-tab ${activeTab === 'login' ? 'active' : ''}`}
            onClick={() => { setActiveTab('login'); setError(''); }}
          >
            Log In
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'signup'}
            className={`auth-tab ${activeTab === 'signup' ? 'active' : ''}`}
            onClick={() => { setActiveTab('signup'); setError(''); }}
          >
            Sign Up
          </button>
        </div>

        {/* Demo accounts - only show on login tab */}
        {activeTab === 'login' && (
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
        )}

        {/* Forms */}
        {activeTab === 'login' && (
          <form className="auth-form" onSubmit={handleLogin} id="login-form">
            <div className="field-group">
              <label className="field-label" htmlFor="email">Email address</label>
              <input
                id="email"
                type="email"
                className="input"
                placeholder="you@campus.edu"
                value={loginForm.email}
                onChange={e => setLoginForm(f => ({ ...f, email: e.target.value }))}
                required
                autoComplete="email"
                disabled={loading}
              />
            </div>

            <div className="field-group">
              <label className="field-label" htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                className="input"
                placeholder="••••••••"
                value={loginForm.password}
                onChange={e => setLoginForm(f => ({ ...f, password: e.target.value }))}
                required
                autoComplete="current-password"
                disabled={loading}
              />
            </div>

            {error && (
              <div className="auth-error" role="alert">{error}</div>
            )}

            <button
              id="auth-submit-btn"
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
        )}

        {activeTab === 'signup' && (
          <form className="auth-form" onSubmit={handleSignup} id="signup-form">
            <div className="field-group">
              <label className="field-label" htmlFor="signup-name">Full Name <span className="required">*</span></label>
              <input
                id="signup-name"
                type="text"
                className="input"
                placeholder="John Doe"
                value={signupForm.name}
                onChange={e => setSignupForm(f => ({ ...f, name: e.target.value }))}
                required
                autoComplete="name"
                disabled={loading}
              />
            </div>

            <div className="field-group">
              <label className="field-label" htmlFor="signup-roll">College Roll Number <span className="required">*</span></label>
              <input
                id="signup-roll"
                type="text"
                className="input"
                placeholder="CS2024001"
                value={signupForm.roll_number}
                onChange={e => setSignupForm(f => ({ ...f, roll_number: e.target.value.toUpperCase() }))}
                required
                autoComplete="off"
                disabled={loading}
                style={{ textTransform: 'uppercase' }}
              />
              <p className="form-hint">Your unique college roll number (e.g., CS2024001)</p>
            </div>

            <div className="field-group">
              <label className="field-label" htmlFor="signup-email">College Email Address <span className="required">*</span></label>
              <input
                id="signup-email"
                type="email"
                className="input"
                placeholder="you@campus.edu"
                value={signupForm.email}
                onChange={e => setSignupForm(f => ({ ...f, email: e.target.value }))}
                required
                autoComplete="email"
                disabled={loading}
              />
              <p className="form-hint">A verification link will be sent to this email</p>
            </div>

            <div className="field-group">
              <label className="field-label" htmlFor="signup-password">Password <span className="required">*</span></label>
              <input
                id="signup-password"
                type="password"
                className="input"
                placeholder="••••••••"
                value={signupForm.password}
                onChange={e => setSignupForm(f => ({ ...f, password: e.target.value }))}
                required
                autoComplete="new-password"
                disabled={loading}
                minLength={8}
              />
              <p className="form-hint">Minimum 8 characters</p>
            </div>

            <div className="field-group">
              <label className="field-label" htmlFor="signup-confirm">Confirm Password <span className="required">*</span></label>
              <input
                id="signup-confirm"
                type="password"
                className="input"
                placeholder="••••••••"
                value={signupForm.confirm_password}
                onChange={e => setSignupForm(f => ({ ...f, confirm_password: e.target.value }))}
                required
                autoComplete="new-password"
                disabled={loading}
              />
            </div>

            {error && (
              <div className="auth-error" role="alert">{error}</div>
            )}

            <button
              id="auth-submit-btn"
              type="submit"
              className="btn btn-primary w-full"
              disabled={loading}
              style={{ marginTop: '0.5rem', height: '2.75rem', fontSize: '0.95rem' }}
            >
              {loading ? (
                <span className="spinner" />
              ) : (
                'Create Account →'
              )}
            </button>
          </form>
        )}

        <p className="auth-footer text-xs text-muted">
          By continuing, you agree to our <Link to="/terms" className="underline">Terms of Service</Link> and <Link to="/privacy" className="underline">Privacy Policy</Link>.
        </p>
      </div>
    </div>
  );
}