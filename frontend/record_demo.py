"""
Automated CampusConnect demo video recorder (headless).
Records a ~2.5-minute walkthrough of the Campus AI Event Platform.
"""

from playwright.sync_api import sync_playwright
import os

BASE_URL = "http://127.0.0.1:5173"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings")


def inject_overlay(page, html):
    page.evaluate("""(html) => {
        const existing = document.getElementById('demo-overlay');
        if (existing) existing.remove();
        const div = document.createElement('div');
        div.id = 'demo-overlay';
        div.style.position = 'fixed';
        div.style.top = '0';
        div.style.left = '0';
        div.style.width = '100vw';
        div.style.height = '100vh';
        div.style.background = 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)';
        div.style.color = '#ffffff';
        div.style.display = 'flex';
        div.style.flexDirection = 'column';
        div.style.justifyContent = 'center';
        div.style.alignItems = 'center';
        div.style.zIndex = '9999';
        div.style.fontFamily = 'Inter, system-ui, sans-serif';
        div.style.textAlign = 'center';
        div.style.padding = '2rem';
        div.innerHTML = html;
        document.body.appendChild(div);
        document.body.style.overflow = 'hidden';
    }""", html)


def remove_overlay(page):
    page.evaluate("""() => {
        const div = document.getElementById('demo-overlay');
        if (div) div.remove();
        document.body.style.overflow = '';
    }""")


def inject_caption(page, text):
    page.evaluate("""(text) => {
        const existing = document.getElementById('demo-caption');
        if (existing) existing.remove();
        const div = document.createElement('div');
        div.id = 'demo-caption';
        div.style.position = 'fixed';
        div.style.bottom = '2rem';
        div.style.left = '50%';
        div.style.transform = 'translateX(-50%)';
        div.style.background = 'rgba(15, 23, 42, 0.85)';
        div.style.color = '#ffffff';
        div.style.padding = '0.75rem 1.5rem';
        div.style.borderRadius = '9999px';
        div.style.fontSize = '1.125rem';
        div.style.fontWeight = '500';
        div.style.zIndex = '10000';
        div.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
        div.style.maxWidth = '90vw';
        div.style.textAlign = 'center';
        div.textContent = text;
        document.body.appendChild(div);
    }""", text)


def remove_caption(page):
    page.evaluate("""() => {
        const div = document.getElementById('demo-caption');
        if (div) div.remove();
    }""")


def wait(page, seconds):
    page.wait_for_timeout(int(seconds * 1000))


def try_click(page, selectors, timeout=5000):
    """Try clicking by a list of selectors; return True on success."""
    for sel in selectors:
        try:
            if sel.startswith("text:"):
                page.get_by_text(sel[5:], exact=False).first.click(timeout=timeout)
            elif sel.startswith("role:"):
                parts = sel[5:].split("::", 1)
                role = parts[0]
                name = parts[1] if len(parts) > 1 else None
                if name:
                    page.get_by_role(role, name=name, exact=False).first.click(timeout=timeout)
                else:
                    page.get_by_role(role).first.click(timeout=timeout)
            elif sel.startswith("placeholder:"):
                page.locator(f'input[placeholder*="{sel[12:]}"]').first.click(timeout=timeout)
            elif sel.startswith("css:"):
                page.locator(sel[4:]).first.click(timeout=timeout)
            else:
                page.get_by_text(sel, exact=False).first.click(timeout=timeout)
            return True
        except Exception:
            continue
    return False


def try_fill(page, selectors, value, timeout=5000):
    """Try filling by a list of selectors; return True on success."""
    for sel in selectors:
        try:
            if sel.startswith("placeholder:"):
                page.locator(f'input[placeholder*="{sel[12:]}"]').first.fill(value, timeout=timeout)
                return True
            elif sel.startswith("css:"):
                page.locator(sel[4:]).first.fill(value, timeout=timeout)
                return True
        except Exception:
            continue
    return False


def scene1_title(page):
    inject_overlay(page, """
        <div>
            <div style="font-size: 0.9rem; letter-spacing: 0.2em; text-transform: uppercase; color: #93c5fd; margin-bottom: 1rem;">CampusConnect</div>
            <h1 style="font-size: 3rem; font-weight: 800; margin: 0 0 1rem 0; line-height: 1.2;">AI-Powered Campus<br>Event Discovery &amp; Management</h1>
            <div style="max-width: 600px; margin: 0 auto; opacity: 0.9; line-height: 1.6;">
                <p><strong>Problem:</strong> Campus events are difficult to discover and manage in one place.</p>
                <p><strong>Solution:</strong> One platform for students and organizers — browse, register, and create events with AI assistance.</p>
                <p><strong>Technology:</strong> React &bull; FastAPI &bull; Nexus AI</p>
            </div>
        </div>
    """)
    wait(page, 10)
    remove_overlay(page)


def scene2_landing_auth(page):
    inject_caption(page, "Landing page — discover featured campus events")
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    wait(page, 6)

    inject_caption(page, "Shared login page — student and organizer accounts")
    try_click(page, ["text:Log in / Sign up", "css:#hero-login-btn"])
    page.wait_for_load_state("networkidle")
    wait(page, 6)

    inject_caption(page, "Quick demo sign-in — student account (password hidden)")
    try_click(page, ["text:Student"])
    page.wait_for_load_state("networkidle")
    wait(page, 5)

    remove_caption(page)


def scene3_student(page):
    inject_caption(page, "Discover Events — browse approved campus events")
    try_click(page, ["text:Discover Events", "text:Browse events", "text:Events"])
    page.wait_for_load_state("networkidle")
    wait(page, 5)

    inject_caption(page, "Search events by name, tag, or organiser")
    try_fill(page, ["placeholder:Search by name"], "AI")
    page.wait_for_timeout(1500)
    wait(page, 4)

    try_click(page, ["css:button.clear-btn"])
    wait(page, 1)

    inject_caption(page, "Filter events by category — Workshop")
    try_click(page, ["text:Workshop"])
    wait(page, 4)
    try_click(page, ["text:All"])
    wait(page, 1)

    inject_caption(page, "Open an event detail page")
    try:
        page.locator('.EventCard, .event-card').first.click(timeout=5000)
    except Exception:
        try:
            page.get_by_role("link").first.click(timeout=5000)
        except Exception:
            pass
    page.wait_for_load_state("networkidle")
    wait(page, 4)

    inject_caption(page, "Save an event for later")
    try_click(page, ["text:☆ Save for later", "text:Save"])
    wait(page, 2)

    inject_caption(page, "Register for an event")
    try_click(page, ["text:Register for this event"])
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass
    wait(page, 4)
    try:
        page.go_back()
        page.wait_for_load_state("networkidle")
    except Exception:
        pass
    wait(page, 2)

    inject_caption(page, "My Events — saved events and registrations")
    try_click(page, ["text:My Events"])
    page.wait_for_load_state("networkidle")
    wait(page, 5)

    inject_caption(page, "AI question-answering — ask about campus events")
    try_click(page, ["text:Chat", "text:Campus Event Assistant"])
    page.wait_for_load_state("networkidle")
    wait(page, 3)

    remove_caption(page)


def scene4_organizer(page):
    inject_caption(page, "Switch to organizer account — AI Club")
    try_click(page, ["text:Log out", "text:Sign out"], timeout=3000)
    page.wait_for_load_state("networkidle")
    wait(page, 2)

    try_click(page, ["text:Log in / Sign up", "text:Sign in"])
    page.wait_for_load_state("networkidle")
    wait(page, 2)

    inject_caption(page, "Organizer demo sign-in (password hidden)")
    try_click(page, ["text:AI Club"])
    page.wait_for_load_state("networkidle")
    wait(page, 3)

    inject_caption(page, "Organizer dashboard — manage your events")
    page.wait_for_load_state("networkidle")
    wait(page, 4)

    inject_caption(page, "Create New Event — AI-assisted event creation")
    try_click(page, ["text:Create event", "text:+ Create event"])
    page.wait_for_load_state("networkidle")
    wait(page, 3)

    inject_caption(page, "Extract Event Details — paste announcement, AI fills the form")
    announcement = (
        "National AI Hackathon 2026\n"
        "Join 500+ students in a 36-hour sprint to build AI-powered solutions for real campus challenges. "
        "Form teams of 2-4 and compete for prizes. "
        "Event date: October 18, 2026. Time: 9:00 AM to 9:00 PM. "
        "Venue: Main Auditorium, Block A. Open to all UG and PG students. "
        "Register by October 15, 2026 at https://forms.example.com/ai-hackathon"
    )
    try_fill(page, ["placeholder:announcement"], announcement)
    wait(page, 1)
    try_click(page, ["text:Extract Event Details"])
    wait(page, 5)

    inject_caption(page, "Review and edit AI-extracted fields before saving")
    wait(page, 5)

    inject_caption(page, "Save Draft — event created as draft, ready for review")
    try_click(page, ["text:Save Draft"])
    page.wait_for_load_state("networkidle")
    wait(page, 4)

    inject_caption(page, "Publish Event — make it live on the discovery feed")
    try_click(page, ["text:Publish Event"])
    page.wait_for_load_state("networkidle")
    wait(page, 4)

    remove_caption(page)


def scene5_ai(page):
    inject_caption(page, "Campus Event Assistant — natural language questions about events")
    try_click(page, ["text:Chat", "text:Campus Event Assistant"])
    page.wait_for_load_state("networkidle")
    wait(page, 2)

    inject_caption(page, "Query: 'What hackathons are happening?'")
    try_fill(page, ["placeholder:hackathons"], "What hackathons are happening?")
    wait(page, 1)
    try_click(page, ["text:Ask"])
    wait(page, 6)

    inject_caption(page, "Query: 'Any workshops this month?'")
    try_fill(page, ["placeholder:hackathons"], "Any workshops this month?")
    wait(page, 1)
    try_click(page, ["text:Ask"])
    wait(page, 6)

    remove_caption(page)


def scene6_closing(page):
    inject_overlay(page, """
        <div>
            <div style="font-size: 0.9rem; letter-spacing: 0.2em; text-transform: uppercase; color: #93c5fd; margin-bottom: 1rem;">CampusConnect</div>
            <h1 style="font-size: 3rem; font-weight: 800; margin: 0 0 1rem 0; line-height: 1.2;">Discover. Participate. Organize.</h1>
            <div style="max-width: 600px; margin: 0 auto; opacity: 0.9; line-height: 1.6;">
                <p><strong>Technology Stack:</strong> React + Vite, FastAPI, Nexus AI</p>
                <p><strong>Repository:</strong> github.com/ssshrinidhi03/campus-ai-event-platform</p>
            </div>
        </div>
    """)
    wait(page, 15)
    remove_overlay(page)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # Clean old recordings
    for f in os.listdir(OUTPUT_DIR):
        os.remove(os.path.join(OUTPUT_DIR, f))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=OUTPUT_DIR,
            record_video_size={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        try:
            scene1_title(page)
            scene2_landing_auth(page)
            scene3_student(page)
            scene4_organizer(page)
            scene5_ai(page)
            scene6_closing(page)

            video_path = page.video.path()
            print(f"VIDEO_PATH:{video_path}")

        except Exception as e:
            print(f"ERROR: {e}")
        finally:
            page.close()
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
