import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { eventsApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import './EventDetailPage.css'; // Reuse some layout styles

export default function RegistrationPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, token } = useAuth();
  
  const [event, setEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [formData, setFormData] = useState({
    name: user?.name || '',
    email: user?.email || '',
    college: ''
  });
  
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    async function loadEvent() {
      try {
        const data = await eventsApi.get(id);
        setEvent(data);
      } catch (err) {
        setError('Failed to load event details.');
      } finally {
        setLoading(false);
      }
    }
    loadEvent();
  }, [id]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    
try {
        await eventsApi.register(id, {
          name: formData.name,
          email: formData.email,
          college: formData.college,
        }, token);
        setSuccess(true);
      } catch (err) {
        setError(err.message || 'Registration failed. Please try again.');
      } finally {
        setSubmitting(false);
      }
  };

  if (loading) return <div className="container page-content">Loading...</div>;
  if (error && !event) return <div className="container page-content text-rose">{error}</div>;

  if (success) {
    return (
      <div className="page-layout">
        <div className="container page-content" style={{ maxWidth: '600px', margin: '0 auto', textAlign: 'center' }}>
          <div className="card" style={{ padding: 'var(--space-8)' }}>
            <span style={{ fontSize: '3rem', display: 'block', marginBottom: 'var(--space-4)' }}>✅</span>
            <h2 className="font-display text-2xl font-bold text-emerald" style={{ marginBottom: 'var(--space-2)' }}>Registration Successful</h2>
            <p className="text-secondary" style={{ marginBottom: 'var(--space-6)' }}>
              You are registered for <strong>{event.title}</strong>.
            </p>
            
            <div className="card-glass" style={{ textAlign: 'left', padding: 'var(--space-4)', marginBottom: 'var(--space-6)' }}>
              <div style={{ marginBottom: 'var(--space-2)' }}><strong>Date:</strong> {event.date}</div>
              <div style={{ marginBottom: 'var(--space-2)' }}><strong>Venue:</strong> {event.venue}</div>
              <div><strong>Status:</strong> <span className="badge badge-emerald">REGISTERED</span></div>
            </div>
            
            <div className="flex gap-4 justify-center">
              <Link to="/events" className="btn btn-ghost">Back to Events</Link>
              <Link to="/my-events" className="btn btn-primary">View My Registrations</Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-layout">
      <div className="container page-content" style={{ maxWidth: '600px', margin: '0 auto' }}>
        <button className="back-btn" onClick={() => navigate(-1)} style={{ marginBottom: 'var(--space-4)' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Back
        </button>
        
        <div className="card" style={{ padding: 'var(--space-6)' }}>
          <h1 className="font-display text-2xl font-bold" style={{ marginBottom: 'var(--space-2)' }}>Register for Event</h1>
          <div className="card-glass" style={{ padding: 'var(--space-4)', marginBottom: 'var(--space-6)' }}>
            <h3 className="font-semibold">{event.title}</h3>
            <p className="text-sm text-secondary">{event.date} at {event.venue}</p>
            <p className="text-xs text-muted" style={{ marginTop: 'var(--space-1)' }}>By {event.organizer_name}</p>
          </div>

          {error && <div className="badge badge-rose" style={{ width: '100%', marginBottom: 'var(--space-4)', padding: 'var(--space-3)' }}>{error}</div>}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="text-sm font-medium" style={{ display: 'block', marginBottom: 'var(--space-1)' }}>Full Name *</label>
              <input 
                type="text" 
                name="name"
                className="input" 
                required 
                value={formData.name}
                onChange={handleChange}
              />
            </div>
            
            <div>
              <label className="text-sm font-medium" style={{ display: 'block', marginBottom: 'var(--space-1)' }}>Email *</label>
              <input 
                type="email" 
                name="email"
                className="input" 
                required 
                value={formData.email}
                onChange={handleChange}
              />
            </div>
            
            <div>
              <label className="text-sm font-medium" style={{ display: 'block', marginBottom: 'var(--space-1)' }}>College / Department</label>
              <input 
                type="text" 
                name="college"
                className="input" 
                value={formData.college}
                onChange={handleChange}
              />
            </div>

            <div className="flex gap-4" style={{ marginTop: 'var(--space-4)' }}>
              <button type="button" className="btn btn-ghost" onClick={() => navigate(-1)} style={{ flex: 1 }}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={submitting} style={{ flex: 1 }}>
                {submitting ? 'Registering...' : 'Confirm Registration'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
