import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { MOCK_EVENTS } from '../services/api';
import './OrganizerDashboard.css';

const MOCK_MY_EVENTS = MOCK_EVENTS.slice(0, 3).map((e, i) => ({
  ...e,
  status: i === 0 ? 'APPROVED' : i === 1 ? 'PENDING_APPROVAL' : 'DRAFT',
}));

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
  const { user } = useAuth();

  const stats = [
    { label: 'Total events',     value: MOCK_MY_EVENTS.length,                                          color: 'var(--clr-brand-400)' },
    { label: 'Approved',         value: MOCK_MY_EVENTS.filter(e => e.status === 'APPROVED').length,     color: 'var(--clr-accent-emerald)' },
    { label: 'Pending review',   value: MOCK_MY_EVENTS.filter(e => e.status === 'PENDING_APPROVAL').length, color: 'var(--clr-accent-amber)' },
    { label: 'Drafts',           value: MOCK_MY_EVENTS.filter(e => e.status === 'DRAFT').length,        color: 'var(--clr-text-muted)' },
  ];

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
            {MOCK_MY_EVENTS.map(event => (
              <div key={event.id} className="org-event-row card animate-fade-in">
                <div className="org-event-info">
                  <h3 className="text-sm font-semibold text-primary">{event.title}</h3>
                  <p className="text-xs text-muted" style={{ marginTop: '2px' }}>{event.category} · {event.date}</p>
                </div>
                <span className={`badge ${STATUS_BADGE[event.status]}`}>
                  {STATUS_LABEL[event.status]}
                </span>
                <Link to={`/events/${event.id}`} className="btn btn-ghost btn-sm">View</Link>
              </div>
            ))}
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
