import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { eventsApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import './OrganizerDashboard.css';

export default function MyEventsPage() {
  const { token, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [savedEvents, setSavedEvents] = useState([]);
  const [registrations, setRegistrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('saved'); // 'saved' or 'registered'

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    loadData();
  }, [isAuthenticated, token]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [savedData, regData] = await Promise.all([
        eventsApi.listSavedEvents(token),
        eventsApi.listOrganizerEvents(token).catch(() => []) // This returns organizer events, not user registrations
      ]);
      setSavedEvents(savedData || []);
      // For now, we'll load registrations from saved events as a placeholder
      // In a full implementation, there would be a separate endpoint for user registrations
      setRegistrations([]);
    } catch (e) {
      setError(e.message || 'Unable to load events');
    } finally {
      setLoading(false);
    }
  };

  const handleUnsave = async (eventId) => {
    try {
      await eventsApi.unsaveEvent(eventId, token);
      setSavedEvents(savedEvents.filter(e => e.event_id !== eventId));
    } catch (e) {
      alert(e.message || 'Failed to remove saved event');
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="page-layout">
        <div className="container" style={{ textAlign: 'center', padding: 'var(--space-16) 0' }}>
          <h1 className="font-display text-3xl font-bold" style={{ marginBottom: 'var(--space-4)' }}>
            Please sign in
          </h1>
          <p className="text-secondary" style={{ marginBottom: 'var(--space-6)' }}>
            You need to be logged in to view your saved events.
          </p>
          <Link to="/login" className="btn btn-primary">Sign in</Link>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="page-layout">
        <div className="container" style={{ textAlign: 'center', padding: 'var(--space-16) 0' }}>
          <p className="text-secondary">Loading your events...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-layout">
        <div className="container" style={{ textAlign: 'center', padding: 'var(--space-16) 0' }}>
          <p className="text-secondary">Error: {error}</p>
        </div>
      </div>
    );
  }

  const currentEvents = activeTab === 'saved' ? savedEvents : registrations;
  const currentCount = activeTab === 'saved' ? savedEvents.length : registrations.length;

  return (
    <div className="page-layout">
      <div className="organizer-hero">
        <div className="container">
          <div className="organizer-header">
            <div>
              <p className="text-muted text-sm font-medium">My Events</p>
              <h1 className="font-display text-3xl font-bold" style={{ marginTop: '4px' }}>
                {activeTab === 'saved' ? 'Saved Events' : 'Registrations'}
              </h1>
            </div>
          </div>
        </div>
      </div>

      <div className="container page-content">
        {/* Tab Navigation */}
        <div className="org-section" style={{ marginBottom: 'var(--space-6)' }}>
          <div style={{ display: 'flex', gap: 'var(--space-2)', borderBottom: '1px solid var(--clr-border)', paddingBottom: 'var(--space-2)' }}>
            <button
              className={`btn ${activeTab === 'saved' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setActiveTab('saved')}
            >
              Saved Events ({savedEvents.length})
            </button>
            <button
              className={`btn ${activeTab === 'registered' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setActiveTab('registered')}
            >
              Registrations ({registrations.length})
            </button>
          </div>
        </div>

        {/* Events List */}
        <div className="org-section">
          <div className="org-events-list">
            {currentEvents.length === 0 ? (
              <div className="empty-state" style={{ textAlign: 'center', padding: 'var(--space-12)' }}>
                <span className="empty-icon" style={{ fontSize: '3rem' }}>
                  {activeTab === 'saved' ? '🔖' : '📝'}
                </span>
                <h3 className="font-display text-xl font-semibold" style={{ marginTop: 'var(--space-4)' }}>
                  {activeTab === 'saved' ? 'No saved events yet' : 'No registrations yet'}
                </h3>
                <p className="text-secondary text-sm" style={{ marginTop: 'var(--space-2)' }}>
                  {activeTab === 'saved' 
                    ? 'Click the bookmark icon on any event card to save it for later.' 
                    : 'Register for events to see them here.'
                  }
                </p>
                <Link to="/events" className="btn btn-primary" style={{ marginTop: 'var(--space-4)', display: 'inline-block' }}>
                  {activeTab === 'saved' ? 'Discover Events' : 'Browse Events'}
                </Link>
              </div>
            ) : (
              currentEvents.map(event => (
                <div key={event.id} className="org-event-row card animate-fade-in">
                  <div className="org-event-info">
                    <h3 className="text-sm font-semibold text-primary">{event.event_title}</h3>
                    <p className="text-xs text-muted" style={{ marginTop: '2px' }}>
                      {event.event_category} · {event.event_date ? event.event_date.split('T')[0] : 'TBD'} · {event.event_venue || 'TBD'}
                    </p>
                  </div>
                  <span className="badge badge-brand">{activeTab === 'saved' ? 'Saved' : 'Registered'}</span>
                  <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                    <Link to={`/events/${event.event_id}`} className="btn btn-ghost btn-sm">View</Link>
                    {activeTab === 'saved' && (
                      <button 
                        onClick={() => handleUnsave(event.event_id)} 
                        className="btn btn-ghost btn-sm" 
                        style={{ color: 'var(--clr-accent-rose)' }}
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}