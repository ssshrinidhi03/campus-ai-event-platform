import { Link, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { eventsApi } from '../services/api';
import './OrganizerDashboard.css';

const STATUS_BADGE = {
  APPROVED:         'badge-emerald',
  PENDING_APPROVAL: 'badge-amber',
  DRAFT:            'badge-brand',
  REJECTED:         'badge-rose',
  CANCELLED:        'badge-rose',
};

const STATUS_LABEL = {
  APPROVED:         'Approved',
  PENDING_APPROVAL: 'Pending review',
  DRAFT:            'Draft',
  REJECTED:         'Rejected',
  CANCELLED:        'Cancelled',
};

export default function OrganizerDashboard() {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const data = await eventsApi.listOrganizerEvents(token);
        setEvents(data);
      } catch (e) {
        setError(e.message || 'Unable to load events');
      } finally {
        setLoading(false);
      }
    };
    fetchEvents();
  }, [token]);

  const stats = [
    { label: 'Total events',     value: events.length,                                           color: 'var(--clr-brand-400)' },
    { label: 'Published',        value: events.filter(e => e.status === 'APPROVED').length,      color: 'var(--clr-accent-emerald)' },
    { label: 'Drafts',           value: events.filter(e => e.status === 'DRAFT').length,         color: 'var(--clr-text-muted)' },
  ];

  const handleDelete = async (eventId) => {
    if (!window.confirm('Are you sure you want to delete this draft?')) return;
    try {
      await eventsApi.deleteEvent(eventId, token);
      setEvents(events.filter(e => e.id !== eventId));
    } catch (e) {
      alert(e.message || 'Failed to delete event');
    }
  };

  const handlePublish = async (eventId) => {
    try {
      await eventsApi.publishEvent(eventId, token);
      setEvents(events.map(e => e.id === eventId ? { ...e, status: 'APPROVED' } : e));
    } catch (e) {
      alert(e.message || 'Failed to publish event');
    }
  };

  const handleEdit = (eventId) => {
    navigate(`/organizer/edit/${eventId}`);
  };

  if (loading) {
    return (
      <div className="page-layout">
        <div className="container" style={{ textAlign: 'center', padding: 'var(--space-16) 0' }}>
          <p className="text-secondary">Loading dashboard...</p>
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

  return (
    <div className="page-layout">
      <div className="organizer-hero">
        <div className="container">
          <div className="organizer-header">
            <div>
              <p className="text-muted text-sm font-medium">Welcome back,</p>
              <h1 className="font-display text-3xl font-bold" style={{ marginTop: '4px' }}>
                {user?.name || 'Organiser'}
              </h1>
            </div>
            <Link to="/organizer/create" id="create-event-btn" className="btn btn-primary">
              + Create event
            </Link>
          </div>
        </div>
      </div>

      <div className="container page-content">
        {/* Stats */}
        <div className="org-stats-grid">
          {stats.map(s => (
            <div key={s.label} className="org-stat-card card animate-fade-in">
              <span className="org-stat-value font-display" style={{ color: s.color }}>{s.value}</span>
              <span className="text-muted text-sm">{s.label}</span>
            </div>
          ))}
        </div>

        {/* My events */}
        <div className="org-section">
          <div className="section-header" style={{ marginBottom: 'var(--space-5)' }}>
            <h2 className="font-display text-xl font-bold">My events</h2>
            <Link to="/organizer/events" className="btn btn-ghost btn-sm">View all →</Link>
          </div>

          <div className="org-events-list">
            {events.length === 0 ? (
              <div className="empty-state" style={{ textAlign: 'center', padding: 'var(--space-8)' }}>
                <span className="empty-icon" style={{ fontSize: '3rem' }}>📅</span>
                <h3 className="font-display text-xl font-semibold" style={{ marginTop: 'var(--space-4)' }}>No events yet</h3>
                <p className="text-secondary text-sm" style={{ marginTop: 'var(--space-2)' }}>Create your first event to get started.</p>
                <Link to="/organizer/create" className="btn btn-primary" style={{ marginTop: 'var(--space-4)', display: 'inline-block' }}>
                  + Create event
                </Link>
              </div>
            ) : (
              events.map(event => (
                <div key={event.id} className="org-event-row card animate-fade-in">
                  <div className="org-event-info">
                    <h3 className="text-sm font-semibold text-primary">{event.title}</h3>
                    <p className="text-xs text-muted" style={{ marginTop: '2px' }}>{event.category} · {event.date?.split('T')[0] || 'TBD'}</p>
                  </div>
                  <span className={`badge ${STATUS_BADGE[event.status] || 'badge-brand'}`}>
                    {STATUS_LABEL[event.status] || event.status}
                  </span>
                  <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                    <Link to={`/organizer/events/${event.id}`} className="btn btn-ghost btn-sm">View</Link>
                    {event.status === 'DRAFT' && (
                      <>
                        <button onClick={() => handleEdit(event.id)} className="btn btn-primary btn-sm">Edit</button>
                        <button onClick={() => handlePublish(event.id)} className="btn btn-primary btn-sm">Publish Event</button>
                        <button onClick={() => handleDelete(event.id)} className="btn btn-ghost btn-sm" style={{ color: 'var(--clr-accent-rose)' }}>Delete</button>
                      </>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Upload notice CTA */}
        <div className="upload-cta card-glass">
          <div className="upload-cta-icon">📄</div>
          <div className="upload-cta-text">
            <h3 className="font-semibold text-primary">Upload an event notice</h3>
            <p className="text-secondary text-sm">
              Our AI will automatically extract event details from your flyer, PDF, or poster.
              <br /><span className="text-muted text-xs">(Document upload available in Phase 5)</span>
            </p>
          </div>
          <button className="btn btn-outline btn-sm" disabled style={{ opacity: 0.6 }}>
            Coming soon
          </button>
        </div>
      </div>
    </div>
  );
}
