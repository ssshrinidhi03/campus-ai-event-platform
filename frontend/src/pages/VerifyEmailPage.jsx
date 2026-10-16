import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../services/api';
import './AuthPage.css';

export default function VerifyEmailPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [email, setEmail] = useState('');
  const [resendLoading, setResendLoading] = useState(false);

  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, isAuthenticated, isVerified, setVerified } = useAuth();

  // If already authenticated and verified, send to events
  if (isAuthenticated && isVerified) {
    navigate('/events', { replace: true });
  }

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setLoading(false);
      return;
    }

    authApi.verifyEmail(token)
      .then(() => {
        // Mark the local user as verified
        const updatedUser = user ? { ...user, is_verified: true } : null;
        if (updatedUser) {
          setVerified(updatedUser);
        }
        setSuccess(true);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Verification failed. Please try again or request a new verification email.');
        setLoading(false);
      });
  }, [searchParams, user, setVerified]);

  const handleResend = async (e) => {
    e.preventDefault();
    if (!email.trim()) {
      setError('Please enter your email address.');
      return;
    }
    setResendLoading(true);
    setError('');
    try {
      await authApi.resendVerification(email.trim());
      setError('A new verification link has been sent to your email. Please check your inbox.');
    } catch (err) {
      setError(err.message || 'Failed to resend verification email.');
    } finally {
      setResendLoading(false);
    }
  };

  const handleGoToLogin = () => {
    navigate('/login');
  };

  if (success) {
    return (
      <div className="auth-page">
        <div className="auth-box card-glass animate-fade-in">
          <div className="auth-header">
            <span className="auth-logo-icon">✅</span>
            <h1 className="auth-title font-display">Email Verified</h1>
            <p className="text-secondary text-sm">
              Your email address has been successfully verified.
            </p>
          </div>

          <div className="auth-footer" style={{ textAlign: 'center' }}>
            <p className="text-muted">You can now log in to your account.</p>
            <button
              onClick={handleGoToLogin}
              className="btn btn-primary"
              style={{ marginTop: '1rem' }}
            >
              Go to Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-box card-glass animate-fade-in">
        <div className="auth-header">
          <span className="auth-logo-icon">✉️</span>
          <h1 className="auth-title font-display">Verify Email</h1>
          <p className="text-secondary text-sm">
            Confirm your email address to activate your account.
          </p>
        </div>

        {loading && (
          <div className="auth-footer" style={{ textAlign: 'center', padding: '2rem 0' }}>
            <span className="spinner" /> Verifying your email...
          </div>
        )}

        {!loading && !success && (
          <>
            {error && (
              <div className="auth-error" role="alert">{error}</div>
            )}

            <form onSubmit={handleResend} className="auth-form" style={{ marginTop: '1rem' }}>
              <div className="field-group">
                <label className="field-label" htmlFor="resend-email">Resend verification link to:</label>
                <input
                  id="resend-email"
                  type="email"
                  className="input"
                  placeholder="you@campus.edu"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  disabled={resendLoading}
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary w-full"
                disabled={resendLoading}
                style={{ marginTop: '1rem' }}
              >
                {resendLoading ? <span className="spinner" /> : 'Resend Verification Email'}
              </button>
            </form>

            <p className="auth-footer text-xs text-muted" style={{ textAlign: 'center', marginTop: '1rem' }}>
              Already verified?{' '}
              <button
                onClick={handleGoToLogin}
                className="underline"
                style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', padding: 0 }}
              >
                Log in
              </button>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
