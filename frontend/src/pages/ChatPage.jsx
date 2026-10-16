import { useState } from 'react';
import './ChatPage.css';
import { aiApi } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function ChatPage() {
  const { token } = useAuth();
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [response, setResponse] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    setResponse(null);
    try {
      const res = await aiApi.queryEvents(query, token);
      setResponse(res);
    } catch (err) {
      setError(err.message || 'Failed to get response');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h1>Campus Event Assistant</h1>
        <p>Ask questions about campus events using natural language</p>
      </div>

      <form onSubmit={handleSubmit} className="chat-form">
        <input type="text" value={query} onChange={(e)=>setQuery(e.target.value)} placeholder="e.g., What hackathons are happening?" className="chat-input" disabled={loading}/>
        <button type="submit" className="chat-submit" disabled={loading || !query.trim()}>{loading?'Thinking...':'Ask'}</button>
      </form>

      {error && (<div className="chat-error" role="alert">{error}</div>)}
      {loading && (<div className="chat-loading" aria-live="polite"><div className="loading-spinner"></div><p>Searching events...</p></div>)}
      {response && !loading && (
        <div className="chat-response" aria-live="polite">
          <div className="answer-section"><h2>Answer</h2><p>{response.answer}</p></div>
          {response.events && response.events.length>0 ? (
            <div className="events-section"><h2>Relevant Events ({response.events.length})</h2>
              <div className="events-list">
                {response.events.map((ev)=>(
                  <div key={ev.id} className="event-card">
                    <h3>{ev.title}</h3>
                    <div className="event-meta">
                      {ev.date && <span>{ev.date}</span>}
                      {ev.category && <span>{ev.category}</span>}
                      {ev.venue && <span>{ev.venue}</span>}
                    </div>
                    <a href={/events/} className="event-link">View Details</a>
                  </div>
                ))}
              </div>
            </div>
          ) : (<div className="no-events" role="status"><p>No relevant events found.</p></div>)}
        </div>
      )}
      {!response && !loading && !error && (
        <div className="chat-empty" role="status">
          <p>Ask me anything about campus events!</p>
          <div className="suggestions">
            <button onClick={()=>setQuery('What workshops are coming up?')}>What workshops?</button>
            <button onClick={()=>setQuery('Any hackathons this month?')}>Hackathons</button>
            <button onClick={()=>setQuery('Tech events')}>Tech events</button>
          </div>
        </div>
      )}
    </div>
  );
}
