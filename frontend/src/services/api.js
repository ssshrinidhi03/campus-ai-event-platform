/**
 * API Service Layer
 * Centralises all HTTP communication with the FastAPI backend.
 * Base URL: http://127.0.0.1:8000
 *
 * IMPORTANT: Only endpoints that actually exist in the backend are called here.
 * Future endpoints are documented with a "PLANNED" comment and return mock data.
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// ── Helpers ─────────────────────────────────────────────────────────────────

async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  let response;
  try {
    // Merge headers: default Content-Type + any custom headers from options
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('Failed to fetch')) {
      throw new Error('Unable to connect to the server. Please make sure the backend is running.');
    }
    throw err;
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// ── Health (IMPLEMENTED – Phase 1) ──────────────────────────────────────────

export const healthApi = {
  /** GET /health  → { status: "ok" } */
  check: () => request('/health'),
};

// ── Auth (IMPLEMENTED – Phase 3) ─────────────────────────────────────────────────

export const authApi = {
  /** POST /api/v1/auth/login */
  login: async (email, password) => {
    return request('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  /** POST /api/v1/auth/logout */
  logout: async () => {
    return request('/api/v1/auth/logout', {
      method: 'POST',
    });
  },

  /** POST /api/v1/auth/register */
  register: async (name, email, password, roll_number) => {
    return request('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password, confirm_password: password, roll_number, account_type: "STUDENT" }),
    });
  },

  /** POST /api/v1/auth/verify-email */
  verifyEmail: async (token) => {
    return request('/api/v1/auth/verify-email', {
      method: 'POST',
      body: JSON.stringify({ token }),
    });
  },

  /** POST /api/v1/auth/resend-verification */
  resendVerification: async (email) => {
    return request('/api/v1/auth/resend-verification', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  },
};

// ── Events (PLANNED – Phase 4) ───────────────────────────────────────────────

export const eventsApi = {
  /** GET /api/v1/events */
  list: async (params = {}) => {
    // params can include query, filters in future
    const query = new URLSearchParams(params).toString();
    const path = `/api/v1/events${query ? `?${query}` : ''}`;
    return request(path);
  },

  /** GET /api/v1/organizer/events */
  listOrganizerEvents: async (token) => {
    return request('/api/v1/organizer/events', {
      headers: {
        'Authorization': `Bearer ${token}`,
      }
    });
  },

  /** GET /api/v1/events/:id */
  get: async (id) => {
    return request(`/api/v1/events/${id}`);
  },
  
  /** POST /api/v1/events/:id/register */
  register: async (id, data, token) => {
    return request(`/api/v1/events/${id}/register`, {
      method: 'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      body: JSON.stringify(data)
    });
  },

  /** POST /api/v1/organizer/events */
  createEvent: async (data, token) => {
    return request('/api/v1/organizer/events', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(data)
    });
  },

  /** PUT /api/v1/organizer/events/:id */
  updateEvent: async (id, data, token) => {
    return request(`/api/v1/organizer/events/${id}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(data)
    });
  },

  /** DELETE /api/v1/organizer/events/:id */
  deleteEvent: async (id, token) => {
    return request(`/api/v1/organizer/events/${id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      }
    });
  },

  /** POST /api/v1/organizer/events/:id/publish */
  publishEvent: async (id, token) => {
    return request(`/api/v1/organizer/events/${id}/publish`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      }
    });
  },

  /** GET /api/v1/organizer/events/:id */
  getOrganizerEvent: async (id, token) => {
    return request(`/api/v1/organizer/events/${id}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      }
    });
  },

  /** POST /api/v1/events/:id/save */
  saveEvent: async (id, token) => {
    return request(`/api/v1/events/${id}/save`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      }
    });
  },

  /** DELETE /api/v1/events/:id/save */
  unsaveEvent: async (id, token) => {
    return request(`/api/v1/events/${id}/save`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      }
    });
  },

  /** GET /api/v1/saved-events */
  listSavedEvents: async (token) => {
    return request('/api/v1/saved-events', {
      headers: {
        'Authorization': `Bearer ${token}`,
      }
    });
  },

  /** GET /api/v1/registrations */
  listRegistrations: async (token) => {
    return request('/api/v1/registrations', {
      headers: {
        'Authorization': `Bearer ${token}`,
      }
    });
  },
};

// ── AI (IMPLEMENTED – Phase 5) ─────────────────────────────────────────────────

export const aiApi = {
  /** POST /api/v1/ai/extract-event */
  extractEvent: async (text, token, imageBase64 = null, imageMimeType = null) => {
    const body = { text };
    if (imageBase64) {
      body.image_base64 = imageBase64;
      body.image_mime_type = imageMimeType;
    }
    return request('/api/v1/ai/extract-event', {
      method: 'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      body: JSON.stringify(body)
    });
  },

  /** POST /api/v1/ai/query */
  queryEvents: async (query, token, options = {}) => {
    return request('/api/v1/ai/query', {
      method: 'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      body: JSON.stringify({ query, ...options })
    });
  },

  /** GET /api/v1/ai/health */
  health: async () => {
    return request('/api/v1/ai/health');
  },
};

// ── Mock data (removed once real APIs are available) ─────────────────────────

export const MOCK_EVENTS = [
  {
    id: 1,
    title: 'National AI Hackathon 2026',
    description: 'Join 500+ students in a 36-hour sprint to build AI-powered solutions for real campus challenges. Form teams of 2–4 and compete for ₹1,00,000 in prizes.',
    category: 'Hackathon',
    date: '2026-10-18',
    start_time: '09:00',
    end_time: '21:00',
    venue: 'Main Auditorium, Block A',
    eligibility: 'All UG and PG students',
    registration_deadline: '2026-10-15T23:59:00',
    registration_link: 'https://forms.example.com/ai-hackathon',
    status: 'APPROVED',
    organizer_id: 2,
    organizer_name: 'AI Club',
    tags: ['AI', 'Machine Learning', 'Prizes', 'Teamwork'],
  },
  {
    id: 2,
    title: 'Deep Learning Workshop Series',
    description: 'A hands-on 3-session workshop covering neural networks, CNNs, and transformer architectures using PyTorch. Laptop required.',
    category: 'Workshop',
    date: '2026-10-22',
    start_time: '14:00',
    end_time: '17:00',
    venue: 'Lab 204, CS Block',
    eligibility: 'CS and IT students (2nd year and above)',
    registration_deadline: '2026-10-20T23:59:00',
    registration_link: 'https://forms.example.com/dl-workshop',
    status: 'APPROVED',
    organizer_id: 2,
    organizer_name: 'ML Society',
    tags: ['Deep Learning', 'PyTorch', 'Hands-on'],
  },
  {
    id: 3,
    title: 'Inter-College Coding Competition',
    description: 'Test your DSA and competitive programming skills against students from 20+ colleges. Individual event with 3 rounds of increasing difficulty.',
    category: 'Competition',
    date: '2026-11-02',
    start_time: '10:00',
    end_time: '16:00',
    venue: 'Computer Centre, Ground Floor',
    eligibility: 'All students',
    registration_deadline: '2026-10-28T23:59:00',
    registration_link: 'https://forms.example.com/coding-comp',
    status: 'APPROVED',
    organizer_id: 3,
    organizer_name: 'Coding Club',
    tags: ['DSA', 'Competitive Programming', 'Inter-college'],
  },
  {
    id: 4,
    title: 'Campus Startup Pitch Day',
    description: 'Present your startup idea to a panel of VCs and angel investors. Top 3 pitches win incubation support and seed funding of up to ₹5 lakhs.',
    category: 'Seminar',
    date: '2026-10-30',
    start_time: '11:00',
    end_time: '15:00',
    venue: 'Innovation Hub, 3rd Floor',
    eligibility: 'All students with a registered startup idea',
    registration_deadline: '2026-10-25T23:59:00',
    registration_link: 'https://forms.example.com/pitch-day',
    status: 'APPROVED',
    organizer_id: 4,
    organizer_name: 'E-Cell',
    tags: ['Startup', 'Pitch', 'Funding', 'Entrepreneurship'],
  },
  {
    id: 5,
    title: 'Web3 and Blockchain Bootcamp',
    description: 'Learn Solidity, smart contracts, and DApp development from industry practitioners. Build and deploy your first decentralised app on testnet.',
    category: 'Workshop',
    date: '2026-11-08',
    start_time: '09:30',
    end_time: '17:30',
    venue: 'Seminar Hall B, Block C',
    eligibility: 'All interested students',
    registration_deadline: '2026-11-05T23:59:00',
    registration_link: 'https://forms.example.com/web3-bootcamp',
    status: 'APPROVED',
    organizer_id: 2,
    organizer_name: 'Blockchain Society',
    tags: ['Web3', 'Blockchain', 'Solidity', 'DApp'],
  },
  {
    id: 6,
    title: 'Photography & Drone Workshop',
    description: 'Master drone cinematography and photo editing. Certified instructors, DJI equipment provided. Certificate of participation for all attendees.',
    category: 'Workshop',
    date: '2026-11-15',
    start_time: '10:00',
    end_time: '13:00',
    venue: 'Sports Ground & AV Room',
    eligibility: 'Open to all',
    registration_deadline: '2026-11-12T23:59:00',
    registration_link: 'https://forms.example.com/drone-workshop',
    status: 'APPROVED',
    organizer_id: 5,
    organizer_name: 'Photography Club',
    tags: ['Photography', 'Drone', 'Creative', 'Certificate'],
  },
];

export const CATEGORY_COLORS = {
  Hackathon:  'badge-violet',
  Workshop:   'badge-brand',
  Competition: 'badge-amber',
  Seminar:    'badge-cyan',
  Conference: 'badge-emerald',
  Cultural:   'badge-rose',
};
