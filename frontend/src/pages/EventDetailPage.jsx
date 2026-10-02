import { useParams, Link, useNavigate } from 'react-router-dom';
import { MOCK_EVENTS, CATEGORY_COLORS } from '../services/api';
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

export default function EventDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const event = MOCK_EVENTS.find(e => e.id === Number(id));

  if (!event) {
    return (
      <div className="page-layout">
        <div className="container page-content not-found">
          <span className="not-found-icon">🔍</span>
          <h2 className="font-display text-2xl font-bold">Event not found</h2>
          <p className="text-secondary">This event may have been removed or the link is incorrect.</p>
          <Link to="/events" className="btn btn-primary">← Back to events</Link>
        </div>
      </div>
    );
  }

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

              {event.registration_link && !isExpired ? (
                <a
                  href={event.registration_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-primary w-full"
                  id={`register-btn-${event.id}`}
                  style={{ justifyContent: 'center', marginTop: 'var(--space-4)' }}
                >
                  Register for this event →
                </a>
              ) : (
                <button className="btn btn-ghost w-full" disabled style={{ marginTop: 'var(--space-4)', opacity: 0.5 }}>
                  Registration closed
                </button>
              )}
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
