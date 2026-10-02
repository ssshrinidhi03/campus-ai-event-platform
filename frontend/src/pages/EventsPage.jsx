import { useState, useMemo } from 'react';
import { MOCK_EVENTS } from '../services/api';
import EventCard from '../components/EventCard';
import './EventsPage.css';

const ALL_CATEGORIES = ['All', ...new Set(MOCK_EVENTS.map(e => e.category))];

export default function EventsPage() {
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('All');

  const filtered = useMemo(() => {
    return MOCK_EVENTS.filter(event => {
      const matchesCategory = activeCategory === 'All' || event.category === activeCategory;
      const q = search.toLowerCase();
      const matchesSearch = !q ||
        event.title.toLowerCase().includes(q) ||
        event.description.toLowerCase().includes(q) ||
        event.tags?.some(t => t.toLowerCase().includes(q)) ||
        event.organizer_name?.toLowerCase().includes(q);
      return matchesCategory && matchesSearch;
    });
  }, [search, activeCategory]);

  return (
    <div className="page-layout">
      <div className="events-page-header">
        <div className="container">
          <div className="events-page-title-row">
            <div>
              <h1 className="font-display text-3xl font-bold">Discover Events</h1>
              <p className="text-secondary text-sm" style={{ marginTop: '0.25rem' }}>
                {filtered.length} events found
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
              onChange={e => setSearch(e.target.value)}
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
                onClick={() => setActiveCategory(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="container page-content">
        {filtered.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">🔍</span>
            <h3 className="font-display text-xl font-semibold">No events found</h3>
            <p className="text-secondary text-sm">Try adjusting your search or filter.</p>
            <button className="btn btn-ghost btn-sm" onClick={() => { setSearch(''); setActiveCategory('All'); }}>
              Clear filters
            </button>
          </div>
        ) : (
          <div className="events-grid">
            {filtered.map((event, i) => (
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
