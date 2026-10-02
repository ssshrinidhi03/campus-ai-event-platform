import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { MOCK_EVENTS } from '../services/api';
import EventCard from '../components/EventCard';
import './HomePage.css';

const STATS = [
  { value: '120+', label: 'Events this semester', color: 'var(--clr-brand-400)' },
  { value: '3,400+', label: 'Students registered', color: 'var(--clr-accent-violet-light)' },
  { value: '40+', label: 'Active clubs', color: 'var(--clr-accent-cyan)' },
  { value: '98%', label: 'Satisfaction rate', color: 'var(--clr-accent-emerald)' },
];

export default function HomePage() {
  const { user } = useAuth();
  const upcoming = MOCK_EVENTS.slice(0, 3);

  return (
    <div className="page-layout">
      {/* Hero */}
      <section className="hero-section">
        <div className="container">
          <div className="hero-content animate-fade-in">
            <span className="hero-eyebrow badge badge-brand">
              ⚡ AI-Powered Event Discovery
            </span>
            <h1 className="hero-title font-display">
              Find events that<br />
              <span className="gradient-text">match your passion</span>
            </h1>
            <p className="hero-subtitle text-secondary">
              Browse workshops, hackathons, seminars and more — discovered and organised
              intelligently across your campus.
            </p>
            <div className="hero-actions">
              <Link to="/events" id="hero-discover-btn" className="btn btn-primary btn-lg">
                Discover events
              </Link>
              {!user && (
                <Link to="/login" className="btn btn-ghost btn-lg">
                  Sign in →
                </Link>
              )}
            </div>
          </div>

          {/* Floating cards decoration */}
          <div className="hero-decoration">
            <div className="deco-card deco-card-1">
              <span className="deco-icon">🏆</span>
              <div>
                <div className="text-sm font-semibold">Hackathon</div>
                <div className="text-xs text-muted">₹1L prize pool</div>
              </div>
            </div>
            <div className="deco-card deco-card-2">
              <span className="deco-icon">🤖</span>
              <div>
                <div className="text-sm font-semibold">AI Workshop</div>
                <div className="text-xs text-muted">2 seats left</div>
              </div>
            </div>
            <div className="deco-card deco-card-3">
              <span className="deco-icon">🚀</span>
              <div>
                <div className="text-sm font-semibold">Pitch Day</div>
                <div className="text-xs text-muted">Register now</div>
              </div>
            </div>
          </div>
        </div>

        {/* Stats bar */}
        <div className="stats-bar">
          <div className="container">
            <div className="stats-grid">
              {STATS.map(s => (
                <div key={s.label} className="stat-item">
                  <span className="stat-value" style={{ color: s.color }}>{s.value}</span>
                  <span className="stat-label text-muted text-sm">{s.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Upcoming events */}
      <section className="upcoming-section">
        <div className="container">
          <div className="section-header">
            <div>
              <h2 className="section-title font-display">Upcoming events</h2>
              <p className="text-secondary text-sm">Don't miss out — deadlines approaching</p>
            </div>
            <Link to="/events" className="btn btn-ghost btn-sm">
              View all →
            </Link>
          </div>

          <div className="events-grid-3">
            {upcoming.map((event, i) => (
              <div key={event.id} style={{ animationDelay: `${i * 80}ms` }}>
                <EventCard event={event} />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA for organizers */}
      <section className="cta-section">
        <div className="container">
          <div className="cta-box card-glass">
            <div className="cta-content">
              <h2 className="font-display text-2xl font-bold">Are you an event organiser?</h2>
              <p className="text-secondary">
                Upload your event notice and let our AI extract event details automatically.
                Publish in minutes, not hours.
              </p>
            </div>
            <Link to="/login" className="btn btn-primary btn-lg" style={{ flexShrink: 0 }}>
              Start organising →
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
