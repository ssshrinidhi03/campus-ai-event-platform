# CampusConnect Demo Test Report

**Video file:** `docs/demo.mp4`
**Recorded:** 2026-10-16
**Application:** Campus AI Event Discovery Platform (React + Vite frontend, FastAPI backend)
**Test environment:** Windows 11, Python 3.13, Node 22, Playwright Chromium (headless, 1920×1080)

---

## Workflows Successfully Demonstrated

| Scene | Workflow | Status | Notes |
|-------|----------|--------|-------|
| 1 | Title card | ✅ | Injected HTML overlay |
| 2 | Landing page loads, shows featured events | ✅ | Real backend API data |
| 2 | Login page with student/organizer demo accounts | ✅ | AuthPage demo buttons visible |
| 2 | Student login (student@campus.edu) | ✅ | Redirects to events page |
| 3 | Discover Events — browse approved events | ✅ | 7 approved events from DB |
| 3 | Search by query ("AI") | ✅ | Backend `/api/v1/events?q=AI` |
| 3 | Filter by category (Workshop / All) | ✅ | Backend `/api/v1/events?category=Workshop` |
| 3 | Open event detail page | ✅ | Shows date, time, venue, eligibility |
| 3 | Save event for later | ✅ | POST `/api/v1/events/{id}/save` |
| 3 | Register for an event | ✅ | POST `/api/v1/events/{id}/register` |
| 3 | My Events — saved events & registrations | ✅ | GET `/api/v1/saved-events`, `/api/v1/registrations` |
| 3 | Chat / AI Q&A interface | ✅ | POST `/api/v1/ai/query` |
| 4 | Organizer login (aiclub@campus.edu) | ✅ | Redirects to organizer dashboard |
| 4 | Organizer dashboard — stats and event list | ✅ | GET `/api/v1/organizer/dashboard` |
| 4 | Create New Event page | ✅ | GET/POST `/api/v1/organizer/events` |
| 4 | AI extraction from announcement text | ✅ | POST `/api/v1/ai/extract-event` (mock provider) |
| 4 | Save draft event | ✅ | Event created with DRAFT status |
| 4 | Publish event | ✅ | POST `/api/v1/organizer/events/{id}/publish` |
| 5 | RAG query: "What hackathons are happening?" | ✅ | Returns answer + relevant events |
| 5 | RAG query: "Any workshops this month?" | ✅ | Returns answer + relevant events |
| 6 | Closing card with tech stack and repo URL | ✅ | Injected HTML overlay |

---

## Limitations and Degraded Features

| Feature | Status | Details |
|---------|--------|---------|
| AI service (Navigate Labs) | ⚠️ Degraded | `NAVIGATE_API_KEY` not configured. Falls back to built-in mock provider. Mock extraction returns demo hackathon data when announcement text contains "hackathon". Mock RAG returns answers based on available event context. |
| Video runtime | ⚠️ Slightly over target | ~3:43 (target: 2–3 minutes). All scenes contain real application footage. |
| Email verification | ⏭️ Skipped | Student accounts are pre-verified in the seed database. No email flow shown (would require SMTP configuration). |
| Document upload / PDF extraction | ⏭️ Skipped | Phase 5 feature — not yet implemented. Dashboard shows "Coming soon" disabled button. |
| Admin moderation | ⏭️ Skipped | Phase 4 feature — organizers can publish directly without admin approval in this deployment. |

---

## Accounts Used (Demo Only)

| Role | Email | Password | Verified |
|------|-------|----------|----------|
| Student | student@campus.edu | student123 | Yes |
| Organizer | aiclub@campus.edu | aiclub123 | Yes |

**Note:** These are test/demo accounts seeded in the development database. Passwords are not shown in the video — demo account buttons on the login page auto-fill credentials without revealing them.

---

## Database State

**Backend database:** `backend/app.db` (SQLite)
**Events seeded:** 9 approved events + 1 draft (from `backend/app/db/seed.py`)

Approved events visible in demo:
1. National AI Hackathon 2026 (Hackathon)
2. AI Workshop (Workshop)
3. Deep Learning Workshop Series (Workshop)
4. Campus Startup Pitch Day (Seminar)
5. Cloud Seminar (Seminar)
6. Inter-College Coding Competition (Competition)
7. Web3 and Blockchain Bootcamp (Workshop)
8. Photography & Drone Workshop (Workshop)

---

## Recording Method

- **Tool:** Playwright (Python) with Chromium browser
- **Mode:** Headless, 1920×1080 viewport
- **Video codec:** VP9 (WebM) → H.264 (MP4) via ffmpeg
- **Overlays:** Title card, scene captions, and closing card injected via JavaScript during recording
- **No narration, no webcam, no fake mouse interactions**

---

## Commands to Preview the Video

```powershell
# Using any media player
start docs\demo.mp4

# Using ffprobe to inspect
ffprobe -i docs/demo.mp4 -show_entries format=duration -v quiet

# Using PowerShell
Invoke-Item docs/demo.mp4
```
