import { useState, useMemo, useEffect, useCallback } from 'react';
import { eventsApi } from '../services/api';
import EventCard from '../components/EventCard';
import './EventsPage.css';

export default function EventsPage() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('All');
  const [searchDebounced, setSearchDebounced] = useState('');

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchDebounced(search.trim());
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Fetch events when search or category changes
  useEffect(() => {
    const fetchEvents = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = {};
        if (searchDebounced) params.q = searchDebounced;
        if (activeCategory && activeCategory !== 'All') params.category = activeCategory;
        
        const data = await eventsApi.list(params);
        setEvents(data.items || data);
      } catch (e) {
        setError(e.message || 'Unable to load events');
      } finally {
        setLoading(false);
      }
    };
    fetchEvents();
  }, [searchDebounced, activeCategory]);

  const ALL_CATEGORIES = useMemo(() => ['All', ...new Set(events.map(e => e.category).filter(Boolean))], [events]);

  const handleCategoryChange = useCallback((cat) => {
    setActiveCategory(cat);
  }, []);

  const handleSearchChange = useCallback((e) => {
    setSearch(e.target.value);
  }, []);

  const handleClearFilters = useCallback(() => {
    setSearch('');
    setActiveCategory('All');
  }, []);

  return (
    <div className="page-layout">
      <div className="events-page-header">
        <div className="container">
          <div className="events-page-title-row">
            <div>
              <h1 className="font-display text-3xl font-bold">Discover Events</h1>
              <p className="text-secondary text-sm" style={{ marginTop: '0.25rem' }}>
                {events.length} events found
              </p>
            </div>
          </div>

          {/* Search bar */}
          <div className="search-bar-wrapper">
            <svg className="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              id="event-search-input"
              className="input search-input"
              placeholder="Search by name, tag, or organiser..."
              value={search}
              onChange={handleSearchChange}
            />
            {search && (
              <button className="clear-btn" onClick={() => setSearch('')} aria-label="Clear search">✕</button>
            )}
          </div>

          {/* Category filters */}
          <div className="filter-row">
            {ALL_CATEGORIES.map(cat => (
              <button
                key={cat}
                id={`filter-${cat.toLowerCase()}`}
                className={`tag ${activeCategory === cat ? 'active' : ''}`}
                onClick={() => handleCategoryChange(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="container page-content">
        {loading ? (
          <div style={{ textAlign: 'center', padding: 'var(--space-16) 0' }}>
            <p className="text-secondary">Loading events...</p>
          </div>
        ) : events.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">🔍</span>
            <h3 className="font-display text-xl font-semibold">No events found</h3>
            <p className="text-secondary text-sm">Try adjusting your search or filter.</p>
            <button className="btn btn-ghost btn-sm" onClick={handleClearFilters}>
              Clear filters
            </button>
          </div>
        ) : (
          <div className="events-grid">
            {events.map((event, i) => (
              <div key={event.id} style={{ animationDelay: `${i * 60}ms` }} className="animate-fade-in">
                <EventCard event={event} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
