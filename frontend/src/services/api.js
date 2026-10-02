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
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

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

// ── Auth (PLANNED – Phase 3) ─────────────────────────────────────────────────

export const authApi = {
  /** PLANNED: POST /api/v1/auth/login */
  login: async (email, password) => {
    // Will call the real endpoint once Phase 3 is implemented.
    // For now, return a mock token so the UI can be developed end-to-end.
    await new Promise(r => setTimeout(r, 600)); // simulate network latency
    if (email && password) {
      return {
        access_token: 'mock_token_' + btoa(email),
        token_type: 'bearer',
        user: {
          id: 1,
          name: email.split('@')[0].replace('.', ' '),
          email,
          role: email.includes('organizer') ? 'ORGANIZER' : email.includes('admin') ? 'ADMIN' : 'STUDENT',
        },
      };
    }
    throw new Error('Invalid credentials');
  },

  /** PLANNED: POST /api/v1/auth/logout */
  logout: async () => {
    await new Promise(r => setTimeout(r, 200));
    return { detail: 'Logged out' };
  },
};

// ── Events (PLANNED – Phase 4) ───────────────────────────────────────────────

export const eventsApi = {
  /** PLANNED: GET /api/v1/events */
  list: async (params = {}) => {
    await new Promise(r => setTimeout(r, 400));
    return { items: MOCK_EVENTS, total: MOCK_EVENTS.length };
  },

  /** PLANNED: GET /api/v1/events/:id */
  get: async (id) => {
    await new Promise(r => setTimeout(r, 300));
    const event = MOCK_EVENTS.find(e => e.id === Number(id));
    if (!event) throw new Error('Event not found');
    return event;
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
