import { useParams, Link, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { eventsApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import './EventDetailPage.css';

function formatDate(d) {
  if (!d) return 'TBD';
  return new Date(d).toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
}

function formatDeadline(d) {
  if (!d) return 'TBD';
  return new Date(d).toLocaleString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function daysLeft(d) {
  if (!d) return null;
  return Math.ceil((new Date(d) - new Date()) / (1000 * 60 * 60 * 24));
}

export default function EventDetailPage({ isOrganizerView = false }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, token, isAuthenticated } = useAuth();
  const [event, setEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [registrations, setRegistrations] = useState([]);
  const [showRegistrations, setShowRegistrations] = useState(false);

  useEffect(() => {
    async function loadEvent() {
      try {
        let data;
        if (isOrganizerView && token) {
          data = await eventsApi.getOrganizerEvent(id, token);
          // Backend returns registrations within the event detail response
          setRegistrations(data.registrations || []);
        } else {
          data = await eventsApi.get(id);
        }
        setEvent(data);
      } catch (err) {
        setError('Event not found');
      } finally {
        setLoading(false);
      }
    }
    loadEvent();
  }, [id, isOrganizerView, token]);

  const handleSave = async () => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    if (!token) return;
    setSaving(true);
    try {
      if (saved) {
        await eventsApi.unsaveEvent(id, token);
        setSaved(false);
      } else {
        await eventsApi.saveEvent(id, token);
        setSaved(true);
      }
    } catch (err) {
      console.error('Save error:', err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="page-layout">
        <div className="container page-content" style={{ textAlign: 'center', padding: 'var(--space-16) 0' }}>
          <p className="text-secondary">Loading event...</p>
        </div>
      </div>
    );
  }

  if (error || !event) {
    return (
      <div className="page-layout">
        <div className="container page-content not-found">
          <span className="not-found-icon">🔍</span>
          <h2 className="font-display text-2xl font-bold">Event not found</h2>
          <p className="text-secondary">This event may have been removed or the link is incorrect.</p>
          <Link to={isOrganizerView ? '/organizer' : '/events'} className="btn btn-primary">
            ← Back to {isOrganizerView ? 'dashboard' : 'events'}
          </Link>
        </div>
      </div>
    );
  }

  const CATEGORY_COLORS = {
    Hackathon:  'badge-violet',
    Workshop:   'badge-brand',
    Competition: 'badge-amber',
    Seminar:    'badge-cyan',
    Conference: 'badge-emerald',
    Cultural:   'badge-rose',
    Sports:     'badge-emerald',
    Other:      'badge-brand',
  };
  
  const badgeClass = CATEGORY_COLORS[event.category] || 'badge-brand';
  const days = daysLeft(event.registration_deadline);
  const isExpired = days !== null && days < 0;

  return (
    <div className="page-layout">
      {/* Header banner */}
      <div className="event-detail-banner">
        <div className="container">
          <button className="back-btn" onClick={() => navigate(-1)}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polyline points="15 18 9 12 15 6" />
            </svg>
            Back
          </button>
        </div>
      </div>

      <div className="container page-content">
        <div className="event-detail-layout">
          {/* Main content */}
          <main className="event-detail-main animate-fade-in">
            {/* Category + status */}
            <div className="flex gap-3" style={{ flexWrap: 'wrap', alignItems: 'center' }}>
              <span className={`badge ${badgeClass}`}>{event.category}</span>
              {!isExpired && days !== null && days <= 5 && (
                <span className="badge badge-rose">⚡ {days} day{days !== 1 ? 's' : ''} left to register</span>
              )}
              {isExpired && <span className="badge badge-amber">Registration closed</span>}
            </div>

            <h1 className="event-detail-title font-display">{event.title}</h1>
            <p className="event-detail-organizer text-muted text-sm">Organised by <strong className="text-secondary">{event.organizer_name}</strong></p>

            <div className="event-detail-description">
              <h2 className="detail-section-title">About this event</h2>
              <p className="text-secondary" style={{ lineHeight: 1.8 }}>{event.description}</p>
            </div>

            {/* Tags */}
            {event.tags?.length > 0 && (
              <div>
                <h2 className="detail-section-title">Tags</h2>
                <div className="flex gap-2" style={{ flexWrap: 'wrap' }}>
                  {event.tags.map(tag => (
                    <span key={tag} className="tag">{tag}</span>
                  ))}
                </div>
              </div>
            )}
          </main>

          {/* Organizer: Registrations section */}
          {isOrganizerView && registrations.length > 0 && (
            <section className="registrations-section animate-fade-in">
              <div className="registrations-header">
                <button
                  onClick={() => setShowRegistrations(!showRegistrations)}
                  className="btn btn-ghost btn-sm"
                  style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}
                >
                  {showRegistrations ? '▾' : '▾'}
                  Registrations ({registrations.length})
                </button>
              </div>
              {showRegistrations && (
                <div className="registrations-list">
                  {registrations.map(reg => (
                    <div key={reg.id} className="registration-row">
                      <div className="registration-info">
                        <div className="registration-name">{reg.user_name}</div>
                        <div className="registration-meta">
                          {reg.user_email} · {reg.registered_at ? new Date(reg.registered_at).toLocaleDateString() : 'TBD'}
                        </div>
                      </div>
                      <span className={`badge badge-brand`}>{reg.status}</span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {/* Sidebar */}
          <aside className="event-detail-sidebar animate-slide-in">
            <div className="sidebar-card card-glass">
              <h3 className="sidebar-card-title font-semibold text-sm">Event details</h3>

              <div className="detail-rows">
                <DetailRow icon="📅" label="Date" value={formatDate(event.date)} />
                <DetailRow icon="🕐" label="Time" value={event.start_time ? `${event.start_time} – ${event.end_time || '?'}` : 'TBD'} />
                <DetailRow icon="📍" label="Venue" value={event.venue || 'TBD'} />
                <DetailRow icon="👤" label="Eligibility" value={event.eligibility || 'Open to all'} />
                <DetailRow icon="⏰" label="Deadline" value={formatDeadline(event.registration_deadline)} />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', marginTop: 'var(--space-4)' }}>
                {!isExpired ? (
                  <Link
                    to={`/events/${event.id}/register`}
                    className="btn btn-primary w-full"
                    id={`register-btn-${event.id}`}
                    style={{ justifyContent: 'center' }}
                  >
                    Register for this event →
                  </Link>
                ) : (
                  <button className="btn btn-ghost w-full" disabled style={{ opacity: 0.5 }}>
                    Registration closed
                  </button>
                )}
                {isAuthenticated && !isOrganizerView && (
                  <button
                    type="button"
                    className={`btn ${saved ? 'btn-primary' : 'btn-outline'} w-full`}
                    onClick={handleSave}
                    disabled={saving}
                    style={{ justifyContent: 'center' }}
                  >
                    {saving ? 'Saving...' : saved ? '★ Saved' : '☆ Save for later'}
                  </button>
                )}
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

function DetailRow({ icon, label, value }) {
  return (
    <div className="detail-row">
      <span className="detail-row-icon">{icon}</span>
      <div>
        <div className="text-xs text-muted font-medium" style={{ textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
        <div className="text-sm text-primary font-medium" style={{ marginTop: '2px' }}>{value}</div>
      </div>
    </div>
  );
}
