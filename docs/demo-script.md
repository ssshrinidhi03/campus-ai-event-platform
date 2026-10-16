# CampusConnect Demo Video Script

**Video file:** `docs/demo.mp4` (MP4, H.264, 1920×1080, ~2.5 MB, ~3:43 runtime)
**Recorded with:** Playwright (Chromium, headless, 1920×1080)
**Backend:** FastAPI on `http://127.0.0.1:8000`
**Frontend:** React + Vite on `http://127.0.0.1:5173`

---

## Scene-by-Scene Outline

### Scene 1: Introduction (0:00 – 0:10)
**Visual:** Full-screen dark gradient title card with centered text.

**On-screen text:**
- CampusConnect
- AI-Powered Campus Event Discovery & Management
- Problem: Campus events are difficult to discover and manage in one place.
- Solution: One platform for students and organizers — browse, register, and create events with AI assistance.
- Technology: React • FastAPI • Nexus AI

**Captions:** None (title card is self-explanatory).

---

### Scene 2: Landing Page and Authentication (0:10 – 0:25)
**Visual:** Real application landing page, then login page.

**Actions:**
1. Navigate to `http://127.0.0.1:5173/` — homepage loads with featured events.
2. Click "Log in / Sign up" — shared login page opens with student/organizer demo account buttons.
3. Click "Student" demo button — logs in as student, redirects to events page.

**Captions:**
- "Landing page — discover featured campus events"
- "Shared login page — student and organizer accounts"
- "Quick demo sign-in — student account (password hidden)"

---

### Scene 3: Student Experience (0:25 – 0:55)
**Visual:** Authenticated student view of the events platform.

**Actions:**
1. Open Discover Events page — shows 7 approved events.
2. Search for "AI" — filters events by title/description/tags.
3. Clear search, then filter by "Workshop" category, then back to "All".
4. Open an event detail page — shows date, time, venue, eligibility, registration deadline.
5. Click "☆ Save for later" — event is saved/bookmarked.
6. Click "Register for this event" — registration form loads.
7. Navigate to My Events — shows saved events and registrations tabs.
8. Navigate to Chat — AI question-answering interface.

**Captions:**
- "Discover Events — browse approved campus events"
- "Search events by name, tag, or organiser"
- "Filter events by category — Workshop"
- "Open an event detail page"
- "Save an event for later"
- "Register for an event"
- "My Events — saved events and registrations"
- "AI question-answering — ask about campus events"

---

### Scene 4: Organizer Experience (0:55 – 1:45)
**Visual:** Authenticated organizer view (AI Club account).

**Actions:**
1. Log out and sign in as "AI Club" organizer demo account (password hidden).
2. Organizer dashboard — shows stats (total events, published, drafts) and event list.
3. Click "+ Create event" — opens Create Event page.
4. Paste a demo announcement into the "Extract from Announcement" textarea.
5. Click "Extract Event Details" — AI populates form fields (title, category, venue, date, times, etc.).
6. Review extracted fields — viewer can see they are editable.
7. Click "Save Draft" — event created as draft, redirects to organizer dashboard.
8. Click "Publish Event" — event status changes to APPROVED, visible on discovery feed.

**Captions:**
- "Switch to organizer account — AI Club"
- "Organizer dashboard — manage your events"
- "Create New Event — AI-assisted event creation"
- "Extract Event Details — paste announcement, AI fills the form"
- "Review and edit AI-extracted fields before saving"
- "Save Draft — event created as draft, ready for review"
- "Publish Event — make it live on the discovery feed"

---

### Scene 5: RAG and AI Capabilities (1:45 – 2:15)
**Visual:** Campus Event Assistant chat interface.

**Actions:**
1. Open Chat page — natural language query interface.
2. Type "What hackathons are happening?" and submit — shows AI answer with relevant events.
3. Type "Any workshops this month?" and submit — shows AI answer with relevant events.

**Captions:**
- "Campus Event Assistant — natural language questions about events"
- "Query: 'What hackathons are happening?'"
- "Query: 'Any workshops this month?'"

**Note:** The AI service runs in degraded mode (no `NAVIGATE_API_KEY` configured), so responses use the built-in mock provider. This is shown honestly in the video — the mock extraction populates the form with demo data, and the RAG chat responds based on available event context.

---

### Scene 6: Closing (2:15 – 2:43)
**Visual:** Full-screen dark gradient closing card.

**On-screen text:**
- CampusConnect
- Discover. Participate. Organize.
- Technology Stack: React + Vite, FastAPI, Nexus AI
- Repository: github.com/ssshrinidhi03/campus-ai-event-platform

**Captions:** None (closing card is self-explanatory).

---

## Total Runtime
Approximately 3 minutes 43 seconds.
