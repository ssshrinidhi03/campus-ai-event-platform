import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import './Navbar.css';

const NAV_LINKS = {
  STUDENT: [
    { to: '/events', label: 'Discover' },
    { to: '/my-events', label: 'My Events' },
  ],
  ORGANIZER: [
    { to: '/organizer', label: 'Dashboard' },
    { to: '/organizer/events', label: 'My Events' },
  ],
  ADMIN: [
    { to: '/admin', label: 'Dashboard' },
  ],
};

export default function Navbar() {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  const links = user ? (NAV_LINKS[user.role] || NAV_LINKS.STUDENT) : [];

  function handleLogout() {
    logout();
    navigate('/login');
  }

  const isActive = (path) => location.pathname === path || location.pathname.startsWith(path + '/');

  return (
    <nav className="navbar">
      <div className="navbar-inner container">
        {/* Logo */}
        <Link to={isAuthenticated ? '/events' : '/'} className="navbar-logo">
          <span className="logo-icon">⚡</span>
          <span className="logo-text">
            Campus<span className="logo-accent">AI</span>
          </span>
        </Link>

        {/* Desktop links */}
        <div className="navbar-links">
          {links.map(link => (
            <Link
              key={link.to}
              to={link.to}
              className={`nav-link ${isActive(link.to) ? 'active' : ''}`}
            >
              {link.label}
            </Link>
          ))}
        </div>

        {/* Right actions */}
        <div className="navbar-actions">
          {isAuthenticated ? (
            <div className="user-menu">
              <button className="user-avatar-btn" onClick={() => setMenuOpen(o => !o)}>
                <span className="avatar-ring">
                  {user.name?.charAt(0).toUpperCase()}
                </span>
                <span className="user-name text-sm font-medium">{user.name}</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </button>
              {menuOpen && (
                <div className="dropdown-menu" onMouseLeave={() => setMenuOpen(false)}>
                  <div className="dropdown-header">
                    <span className="text-sm text-secondary">{user.email}</span>
                    <span className={`badge badge-${user.role === 'ADMIN' ? 'rose' : user.role === 'ORGANIZER' ? 'cyan' : 'brand'} text-xs`}>
                      {user.role}
                    </span>
                  </div>
                  <Link to="/profile" className="dropdown-item" onClick={() => setMenuOpen(false)}>
                    Profile
                  </Link>
                  <button className="dropdown-item dropdown-item-danger" onClick={handleLogout}>
                    Sign out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <>
              <Link to="/login" className="btn btn-ghost btn-sm">Sign in</Link>
              <Link to="/login" className="btn btn-primary btn-sm">Get started</Link>
            </>
          )}
        </div>

        {/* Mobile hamburger */}
        <button
          className={`hamburger ${menuOpen ? 'open' : ''}`}
          onClick={() => setMenuOpen(o => !o)}
          aria-label="Toggle menu"
        >
          <span /><span /><span />
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="mobile-menu">
          {links.map(link => (
            <Link key={link.to} to={link.to} className="mobile-link" onClick={() => setMenuOpen(false)}>
              {link.label}
            </Link>
          ))}
          {isAuthenticated ? (
            <button className="mobile-link mobile-link-danger" onClick={handleLogout}>Sign out</button>
          ) : (
            <Link to="/login" className="mobile-link" onClick={() => setMenuOpen(false)}>Sign in</Link>
          )}
        </div>
      )}
    </nav>
  );
}
