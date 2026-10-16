import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { eventsApi } from '../services/api';
import EventCard from '../components/EventCard';
import './HomePage.css';

const FEATURES = [
  { icon: '🤖', title: 'AI-powered extraction', text: 'Paste an event announcement and let AI fill in the details automatically.' },
  { icon: '📅', title: 'Campus-wide discovery', text: 'Browse workshops, hackathons, seminars and more across your campus.' },
  { icon: '⚡', title: 'Publish in minutes', text: 'Organisers can create and publish events without manual paperwork.' },
  { icon: '🎫', title: 'Easy registration', text: 'Register for events directly from the platform.' },
];

export default function HomePage() {
  const { user } = useAuth();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    const fetchEvents = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await eventsApi.list();
        if (!cancelled) {
          setEvents(Array.isArray(data) ? data : (data.items || []));
        }
      } catch (e) {
        if (!cancelled) {
          setError(e.message || 'Unable to load events. Please try again later.');
          setLoading(false);
        }
      }
      if (!cancelled) {
        setLoading(false);
      }
    };

    fetchEvents();

    return () => {
      cancelled = true;
    };
  }, []);

  const upcoming = events.slice(0, 3);

  if (loading) {
    return (
      <div className="page-layout">
        <div className="container" style={{ textAlign: 'center', padding: 'var(--space-16) 0' }}>
          <p className="text-secondary">Loading events...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-layout">
        <div className="container" style={{ textAlign: 'center', padding: 'var(--space-16) 0' }}>
          <div className="alert alert-error" role="alert">
            {error}
          </div>
          {!user && (
            <Link to="/login" className="btn btn-primary btn-lg" style={{ marginTop: 'var(--space-4)', display: 'inline-block' }}>
              Log in / Sign up
            </Link>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="page-layout">
      {/* Hero */}
      <section className="hero-section">
        <div className="container">
          <div className="hero-content animate-fade-in">
            <span className="hero-eyebrow badge badge-brand">
              ⚡ Campus Event Discovery
            </span>
            <h1 className="hero-title font-display">
              Find events that<br />
              <span className="gradient-text">match your passion</span>
            </h1>
            <p className="hero-subtitle text-secondary">
              Browse workshops, hackathons, seminars and more — organised across your campus.
            </p>
            <div className="hero-actions">
              <Link to="/login" id="hero-login-btn" className="btn btn-primary btn-lg">
                Log in / Sign up
              </Link>
              {!user && (
                <Link to="/events" className="btn btn-ghost btn-lg">
                  Browse events
                </Link>
              )}
            </div>
          </div>
        </div>

        {/* Feature highlights (non-numeric, no fake stats) */}
        <div className="features-section">
          <div className="container">
            <div className="features-grid">
              {FEATURES.map(f => (
                <div key={f.title} className="feature-item card-glass">
                  <span className="feature-icon" style={{ fontSize: '1.75rem' }}>{f.icon}</span>
                  <h3 className="feature-title font-display">{f.title}</h3>
                  <p className="feature-text text-secondary text-sm">{f.text}</p>
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
              <p className="text-secondary text-sm">Published events across campus</p>
            </div>
            <Link to="/events" className="btn btn-ghost btn-sm">
              View all →
            </Link>
          </div>

          {error === null && events.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">📭</span>
              <h3 className="font-display text-xl font-semibold">No events published yet</h3>
              <p className="text-secondary text-sm">Check back soon for upcoming campus events.</p>
            </div>
          ) : (
            <div className="events-grid-3">
              {upcoming.map((event, i) => (
                <div key={event.id} style={{ animationDelay: `${i * 80}ms` }}>
                  <EventCard event={event} />
                </div>
              ))}
            </div>
          )}
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
