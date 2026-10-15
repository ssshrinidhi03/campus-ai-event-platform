from datetime import date, time, datetime, timezone
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, init_db, engine, Base
from app.models.user import User
from app.models.event import Event
from app.models.enums import UserRole, EventStatus
from app.core.security import get_password_hash


def seed_database(db: Session = None):
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # Check if users already exist
        if db.query(User).count() == 0:
            users = [
                User(id=1, name="Student User", email="student@campus.edu", password_hash=get_password_hash("student123"), role=UserRole.STUDENT, roll_number="STU001", is_verified=True, is_identity_verified=False),
                User(id=2, name="AI Club", email="aiclub@campus.edu", password_hash=get_password_hash("aiclub123"), role=UserRole.ORGANIZER, is_verified=True, is_identity_verified=False),
                User(id=3, name="Coding Club", email="codingclub@campus.edu", password_hash=get_password_hash("codingclub123"), role=UserRole.ORGANIZER, is_verified=True, is_identity_verified=False),
                User(id=4, name="E-Cell", email="ecell@campus.edu", password_hash=get_password_hash("ecell123"), role=UserRole.ORGANIZER, is_verified=True, is_identity_verified=False),
                User(id=5, name="Photography Club", email="photoclub@campus.edu", password_hash=get_password_hash("photoclub123"), role=UserRole.ORGANIZER, is_verified=True, is_identity_verified=False),
            ]
            db.add_all(users)
            db.commit()

        # Check if events already exist
        if db.query(Event).count() == 0:
            events = [
                Event(
                    id=1,
                    title="National AI Hackathon 2026",
                    description="Join 500+ students in a 36-hour sprint to build AI-powered solutions for real campus challenges. Form teams of 2–4 and compete for ₹1,00,000 in prizes.",
                    category="Hackathon",
                    organizer_id=2,
                    date=date(2026, 10, 18),
                    start_time=time(9, 0),
                    end_time=time(21, 0),
                    venue="Main Auditorium, Block A",
                    eligibility="All UG and PG students",
                    registration_deadline=datetime(2026, 10, 15, 23, 59, 0, tzinfo=timezone.utc),
                    registration_link="https://forms.example.com/ai-hackathon",
                    tags="AI, Machine Learning, Prizes, Teamwork",
                    status=EventStatus.APPROVED
                ),
                Event(
                    id=2,
                    title="Deep Learning Workshop Series",
                    description="A hands-on 3-session workshop covering neural networks, CNNs, and transformer architectures using PyTorch. Laptop required.",
                    category="Workshop",
                    organizer_id=2,
                    date=date(2026, 10, 22),
                    start_time=time(14, 0),
                    end_time=time(17, 0),
                    venue="Lab 204, CS Block",
                    eligibility="CS and IT students (2nd year and above)",
                    registration_deadline=datetime(2026, 10, 20, 23, 59, 0, tzinfo=timezone.utc),
                    registration_link="https://forms.example.com/dl-workshop",
                    tags="Deep Learning, PyTorch, Hands-on",
                    status=EventStatus.APPROVED
                ),
                Event(
                    id=3,
                    title="Inter-College Coding Competition",
                    description="Test your DSA and competitive programming skills against students from 20+ colleges. Individual event with 3 rounds of increasing difficulty.",
                    category="Competition",
                    organizer_id=3,
                    date=date(2026, 11, 2),
                    start_time=time(10, 0),
                    end_time=time(16, 0),
                    venue="Computer Centre, Ground Floor",
                    eligibility="All students",
                    registration_deadline=datetime(2026, 10, 28, 23, 59, 0, tzinfo=timezone.utc),
                    registration_link="https://forms.example.com/coding-comp",
                    tags="DSA, Competitive Programming, Inter-college",
                    status=EventStatus.APPROVED
                ),
                Event(
                    id=4,
                    title="Campus Startup Pitch Day",
                    description="Present your startup idea to a panel of VCs and angel investors. Top 3 pitches win incubation support and seed funding of up to ₹5 lakhs.",
                    category="Seminar",
                    organizer_id=4,
                    date=date(2026, 10, 30),
                    start_time=time(11, 0),
                    end_time=time(15, 0),
                    venue="Innovation Hub, 3rd Floor",
                    eligibility="All students with a registered startup idea",
                    registration_deadline=datetime(2026, 10, 25, 23, 59, 0, tzinfo=timezone.utc),
                    registration_link="https://forms.example.com/pitch-day",
                    tags="Startup, Pitch, Funding, Entrepreneurship",
                    status=EventStatus.APPROVED
                ),
                Event(
                    id=5,
                    title="Web3 and Blockchain Bootcamp",
                    description="Learn Solidity, smart contracts, and DApp development from industry practitioners. Build and deploy your first decentralised app on testnet.",
                    category="Workshop",
                    organizer_id=2,
                    date=date(2026, 11, 8),
                    start_time=time(9, 30),
                    end_time=time(17, 30),
                    venue="Seminar Hall B, Block C",
                    eligibility="All interested students",
                    registration_deadline=datetime(2026, 11, 5, 23, 59, 0, tzinfo=timezone.utc),
                    registration_link="https://forms.example.com/web3-bootcamp",
                    tags="Web3, Blockchain, Solidity, DApp",
                    status=EventStatus.APPROVED
                ),
                Event(
                    id=6,
                    title="Photography & Drone Workshop",
                    description="Master drone cinematography and photo editing. Certified instructors, DJI equipment provided. Certificate of participation for all attendees.",
                    category="Workshop",
                    organizer_id=5,
                    date=date(2026, 11, 15),
                    start_time=time(10, 0),
                    end_time=time(13, 0),
                    venue="Sports Ground & AV Room",
                    eligibility="Open to all",
                    registration_deadline=datetime(2026, 11, 12, 23, 59, 0, tzinfo=timezone.utc),
                    registration_link="https://forms.example.com/drone-workshop",
                    tags="Photography, Drone, Creative, Certificate",
                    status=EventStatus.APPROVED
                ),
                Event(
                    id=7,
                    title="Generative AI Agents Hands-On",
                    description="Building autonomous tool-using agents with LangChain and Llama. Draft proposal for mid-semester hands-on hack night.",
                    category="Workshop",
                    organizer_id=2,
                    date=date(2026, 11, 25),
                    start_time=time(14, 0),
                    end_time=time(17, 0),
                    venue="Seminar Hall A, Block B",
                    eligibility="Open to all students",
                    registration_deadline=datetime(2026, 11, 20, 23, 59, 0, tzinfo=timezone.utc),
                    registration_link="https://forms.example.com/genai-agents",
                    tags="GenAI, Agents, LLM",
                    status=EventStatus.DRAFT
                ),
                Event(
                    id=8,
                    title="Campus Robotics Showcase",
                    description="Annual showcase of autonomous robots, rovers, and quadcopters. Awaiting faculty advisor clearance.",
                    category="Competition",
                    organizer_id=2,
                    date=date(2026, 12, 5),
                    start_time=time(10, 0),
                    end_time=time(16, 0),
                    venue="Indoor Sports Complex",
                    eligibility="All campus departments",
                    registration_deadline=datetime(2026, 12, 1, 23, 59, 0, tzinfo=timezone.utc),
                    registration_link="https://forms.example.com/robotics",
                    tags="Robotics, Hardware, Exhibition",
                    status=EventStatus.PENDING_APPROVAL
                ),
            ]
            db.add_all(events)
            db.commit()

        print("Database seeded successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        if close_db:
            db.close()


if __name__ == "__main__":
    init_db(engine)
    seed_database()
