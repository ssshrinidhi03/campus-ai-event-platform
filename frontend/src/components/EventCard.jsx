import { CATEGORY_COLORS } from '../services/api';
import { Link } from 'react-router-dom';
import './EventCard.css';

function formatDate(dateStr) {
  if (!dateStr) return 'TBD';
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
}

function daysUntilDeadline(deadlineStr) {
  if (!deadlineStr) return null;
  const diff = new Date(deadlineStr) - new Date();
  const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
  return days;
}

export default function EventCard({ event }) {
  const badgeClass = CATEGORY_COLORS[event.category] || 'badge-brand';
  const days = daysUntilDeadline(event.registration_deadline);
  const isUrgent = days !== null && days <= 3 && days >= 0;
  const isExpired = days !== null && days < 0;

  return (
    <article className="event-card card animate-fade-in">
      {/* Category stripe */}
      <div className={`event-card-stripe stripe-${event.category?.toLowerCase()}`} />

      <div className="event-card-body">
        {/* Header row */}
        <div className="event-card-header">
          <span className={`badge ${badgeClass}`}>{event.category}</span>
          {isUrgent && <span className="badge badge-rose urgency-badge">⚡ {days}d left</span>}
          {isExpired && <span className="badge badge-amber urgency-badge">Closed</span>}
        </div>

        {/* Title */}
        <h3 className="event-title">{event.title}</h3>

        {/* Organizer */}
        <p className="event-organizer">by {event.organizer_name}</p>

        {/* Description snippet */}
        <p className="event-desc">{event.description}</p>

        {/* Meta row */}
        <div className="event-meta">
          <span className="meta-item">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
            {formatDate(event.date)}
          </span>
          <span className="meta-item">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
            </svg>
            {event.venue || 'TBD'}
          </span>
        </div>

        {/* Tags */}
        {event.tags?.length > 0 && (
          <div className="event-tags">
            {event.tags.slice(0, 3).map(tag => (
              <span key={tag} className="tag">{tag}</span>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="event-card-footer">
          <Link to={`/events/${event.id}`} className="btn btn-outline btn-sm">
            View details
          </Link>
          {event.registration_link && !isExpired && (
            <a
              href={event.registration_link}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary btn-sm"
            >
              Register →
            </a>
          )}
        </div>
      </div>
    </article>
  );
}
