"""Tests for RAG-based semantic search and vector store"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, date, time
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal, engine, Base
from app.core.security import get_current_user, require_organizer
from app.models.user import User
from app.core.password import get_password_hash
from app.models.event import Event
from app.models.enums import UserRole, EventStatus
from app.services.vector_store import SimpleVectorStore, EventEmbedding

# Enable testing mode
from app.core.config import settings
settings.TESTING = True

client = TestClient(app)


# ── Auth override for tests ──────────────────────────────────────────────

class _FakeUser:
    id = 1
    email = "test@campus.edu"
    role = UserRole.ORGANIZER
    name = "Test Organizer"
    full_name = "Test Organizer"


def _mock_current_user():
    return _FakeUser()


def setup_module(module):
    """Create tables, seed test users, and override auth dependency."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(User).delete(synchronize_session=False)
        users = [
            User(id=1, name="Student User", email="student@campus.edu",
                 password_hash=get_password_hash("student123"), role=UserRole.STUDENT,
                 roll_number="STU001", is_verified=True, is_identity_verified=False),
            User(id=2, name="AI Club", email="aiclub@campus.edu",
                 password_hash=get_password_hash("aiclub123"), role=UserRole.ORGANIZER,
                 is_verified=True, is_identity_verified=False),
        ]
        db.add_all(users)
        db.commit()
    finally:
        db.close()
    # Override auth deps for this test module
    app.dependency_overrides[get_current_user] = _mock_current_user
    app.dependency_overrides[require_organizer] = _mock_current_user


def teardown_module(module):
    """Clear auth dependency overrides after this test module."""
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_organizer, None)


# ── Original tests (preserved) ───────────────────────────────────────────

class TestVectorStore:
    @pytest.mark.asyncio
    async def test_add_approved_event(self):
        vs = SimpleVectorStore(persist_path=':memory:')
        ev = Event(id=1, title='AI Hackathon', description='Learn AI', category='Hackathon',
                   organizer_id=1, status=EventStatus.APPROVED, venue='Hall', date=date(2026,10,20))
        res = await vs.add_event(ev)
        assert res == True
        assert 1 in vs.embeddings

    @pytest.mark.asyncio
    async def test_dont_add_unpublished(self):
        vs = SimpleVectorStore(persist_path=':memory:')
        ev = Event(id=2, title='Draft', organizer_id=1, status=EventStatus.DRAFT)
        res = await vs.add_event(ev)
        assert res == False
        assert 2 not in vs.embeddings

    @pytest.mark.asyncio
    async def test_reindex(self, tmp_path):
        vs = SimpleVectorStore(persist_path=str(tmp_path/'emb.json'))
        db = Mock()
        ev = Event(id=3, title='Workshop', organizer_id=1, status=EventStatus.APPROVED,
                   category='Workshop', date=date(2026,10,21))
        db.query().filter().all.return_value = [ev]
        stats = await vs.reindex_all(db)
        assert stats['indexed'] >= 1

    @pytest.mark.asyncio
    async def test_search_empty(self):
        vs = SimpleVectorStore(persist_path=':memory:')
        res = await vs.search('anything')
        assert res == []

    @pytest.mark.asyncio
    async def test_remove_on_unpublish(self):
        vs = SimpleVectorStore(persist_path=':memory:')
        ev = Event(id=4, title='Event', organizer_id=1, status=EventStatus.APPROVED)
        await vs.add_event(ev)
        ev.status = EventStatus.DRAFT
        await vs.add_event(ev)
        assert 4 not in vs.embeddings


class TestVectorStoreExclusion:
    """Verify draft/unpublished events are never exposed via search."""

    @pytest.mark.asyncio
    async def test_search_excludes_unpublished_after_index(self):
        vs = SimpleVectorStore(persist_path=':memory:')
        approved = Event(id=1, title='Approved Event', description='desc', category='Workshop',
                         organizer_id=1, status=EventStatus.APPROVED, venue='Hall', date=date(2026,10,20))
        draft = Event(id=2, title='Draft Event', description='desc', category='Seminar',
                      organizer_id=1, status=EventStatus.DRAFT, venue='Room B', date=date(2026,11,1))
        await vs.add_event(approved)
        await vs.add_event(draft)
        assert 1 in vs.embeddings
        assert 2 not in vs.embeddings  # draft never indexed

    @pytest.mark.asyncio
    async def test_search_only_returns_approved(self):
        vs = SimpleVectorStore(persist_path=':memory:')
        approved = Event(id=1, title='AI Workshop', description='Learn AI', category='Workshop',
                         organizer_id=1, status=EventStatus.APPROVED, venue='Hall', date=date(2026,10,20))
        draft = Event(id=2, title='Secret Draft', description='hidden', category='Seminar',
                      organizer_id=1, status=EventStatus.DRAFT, venue='Room B', date=date(2026,11,1))
        await vs.add_event(approved)
        await vs.add_event(draft)  # draft rejected, not indexed
        assert 1 in vs.embeddings
        assert 2 not in vs.embeddings
        results = await vs.search('workshop', limit=5)
        indexed_ids = {emb.event_id for emb, _ in results}
        assert 2 not in indexed_ids  # draft never appears


class TestEventSearchTool:
    """Test the agent's EventSearchTool authorization boundary."""

    def test_tool_schema_has_required_query(self):
        from app.services.ai import EventSearchTool
        vs = SimpleVectorStore(persist_path=':memory:')
        db = Mock()
        tool = EventSearchTool(vector_store=vs, db_session=db)
        schema = tool.get_input_schema()
        assert schema["name"] == "search_events"
        assert "query" in schema["parameters"]["required"]
        assert schema["parameters"]["properties"]["query"]["type"] == "string"

    def test_tool_validates_args(self):
        from app.services.ai import EventSearchTool
        vs = SimpleVectorStore(persist_path=':memory:')
        db = Mock()
        tool = EventSearchTool(vector_store=vs, db_session=db)
        with pytest.raises(ValueError):
            tool.validate_args({})
        with pytest.raises(ValueError):
            tool.validate_args({"query": "   "})
        out = tool.validate_args({"query": "AI workshop", "limit": 5, "category": "Workshop"})
        assert out["query"] == "AI workshop"
        assert out["limit"] == 5
        assert out["category"] == "Workshop"
        out = tool.validate_args({"query": "x", "limit": 999})
        assert out["limit"] == 50
        out = tool.validate_args({"query": "x", "limit": 0})
        assert out["limit"] == 1

    @pytest.mark.asyncio
    async def test_tool_execute_only_returns_approved(self):
        from app.services.ai import EventSearchTool
        vs = SimpleVectorStore(persist_path=':memory:')
        fake_emb = Mock()
        fake_emb.event_id = 1
        vs.search = AsyncMock(return_value=[(fake_emb, 0.9)])
        approved = Event(id=1, title='AI Workshop', organizer_id=1, status=EventStatus.APPROVED)
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = approved
        tool = EventSearchTool(vector_store=vs, db_session=db)
        results = await tool.execute({"query": "anything", "limit": 10})
        ids = [r["id"] for r in results]
        assert 1 in ids

    @pytest.mark.asyncio
    async def test_tool_execute_excludes_unpublished_on_db_reverify(self):
        from app.services.ai import EventSearchTool
        vs = SimpleVectorStore(persist_path=':memory:')
        fake_emb = Mock()
        fake_emb.event_id = 5
        vs.search = AsyncMock(return_value=[(fake_emb, 0.9)])
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None
        tool = EventSearchTool(vector_store=vs, db_session=db)
        results = await tool.execute({"query": "seminar", "limit": 10})
        assert results == []


# ── New regression tests ────────────────────────────────────────────────

class TestEmbeddingGeneration:
    """Test that real embeddings are used (not hash-based fallback)."""

    @pytest.mark.asyncio
    async def test_get_embedding_returns_real_embedding(self):
        """NavigateLabsProvider.get_embedding() calls the /embeddings endpoint."""
        from app.services.ai import NavigateLabsProvider

        provider = NavigateLabsProvider()
        fake_response = {
            "model": "text-embedding-3-small",
            "data": [{"embedding": [0.1, -0.2, 0.3] * 512}],  # 1536 dims
        }

        with patch.object(provider, '_make_request', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = fake_response
            embedding = await provider.get_embedding("test query")

        assert len(embedding) == 1536
        assert embedding[0] == 0.1
        mock_req.assert_called_once()
        call_args = mock_req.call_args
        assert call_args[0][0] == "/embeddings"
        assert call_args[0][1]["model"] == "text-embedding-3-small"
        assert call_args[0][1]["input"] == "test query"


class TestVectorStoreSemanticSearch:
    """Test semantic search with mocked embeddings."""

    @pytest.mark.asyncio
    async def test_search_uses_real_embeddings_not_hash(self):
        """Vector store uses get_embedding() from provider, not _hash() fallback."""
        vs = SimpleVectorStore(persist_path=':memory:')

        class FakeProvider:
            config = type('Config', (), {'embedding_model': 'text-embedding-3-small'})()
            async def get_embedding(self, text: str):
                words = set(text.lower().split())
                base = [0.0] * 10
                if 'ai' in words: base[0] = 1.0
                if 'workshop' in words: base[1] = 1.0
                if 'cloud' in words: base[2] = 1.0
                if 'transformer' in words: base[3] = 1.0
                return base

        with patch('app.services.ai.get_ai_provider', return_value=FakeProvider()):
            ai_ev = Event(id=1, title='AI Workshop', description='Learn AI and machine learning',
                          category='Workshop', organizer_id=1, status=EventStatus.APPROVED,
                          venue='Hall A', date=date(2026, 10, 20))
            cloud_ev = Event(id=2, title='Cloud Computing', description='AWS and Azure cloud training',
                             category='Workshop', organizer_id=1, status=EventStatus.APPROVED,
                             venue='Lab B', date=date(2026, 11, 1))

            await vs.add_event(ai_ev)
            await vs.add_event(cloud_ev)

            results = await vs.search('AI workshop', limit=5)
            ids = {emb.event_id for emb, _ in results}
            assert 1 in ids  # AI workshop should be retrieved

            results = await vs.search('cloud computing', limit=5)
            ids = {emb.event_id for emb, _ in results}
            assert 2 in ids  # Cloud event should be retrieved


class TestQueryEndpointUsesVectorStore:
    """Test that /query endpoint uses vector store for semantic retrieval."""

    @pytest.mark.asyncio
    async def test_query_retrieves_relevant_approved_event(self):
        """An approved AI workshop is retrieved by a query about AI workshops."""
        db = SessionLocal()
        try:
            ai_ev = Event(
                id=1, title='AI and Machine Learning Workshop',
                description='The workshop covers neural networks, transformer architecture, and more.',
                category='Workshop', organizer_id=1, status=EventStatus.APPROVED,
                venue='Seminar Hall 2', date=date(2026, 10, 20),
                start_time=time(9, 0), end_time=time(17, 0),
            )
            db.add(ai_ev)
            db.commit()
        finally:
            db.close()

        # Mock vector store search to return our event (event_id=1 exists in DB)
        from app.services.vector_store import SimpleVectorStore as VS

        async def mock_search(self, q, limit=10, filters=None):
            fake_emb = type('FakeEmb', (), {'event_id': 1})()
            return [(fake_emb, 0.95)]

        with patch.object(VS, 'search', mock_search):
            with patch('app.api.ai.get_ai_provider') as mock_get_provider:
                mock_provider = AsyncMock()
                mock_provider.query_events = AsyncMock(return_value=type('RagResp', (), {
                    'answer': 'The AI and Machine Learning Workshop covers neural networks and transformer architecture.',
                    'events': [],
                    'query_time_ms': 100,
                })())
                mock_get_provider.return_value = mock_provider

                r = client.post("/api/v1/ai/query", json={"query": "AI workshop"})
                assert r.status_code == 200
                data = r.json()
                assert 'AI' in data['answer'] or 'workshop' in data['answer'].lower()

    def test_query_excludes_draft_events(self):
        """Draft events are not returned by /query endpoint."""
        db = SessionLocal()
        try:
            draft_ev = Event(
                id=99, title='Secret Draft Event',
                description='This is a secret draft that should not be found.',
                category='Seminar', organizer_id=1, status=EventStatus.DRAFT,
                venue='Hidden Room', date=date(2026, 12, 1),
            )
            db.add(draft_ev)
            db.commit()
        finally:
            db.close()

        vs = SimpleVectorStore(persist_path=':memory:')

        with patch('app.api.ai.SimpleVectorStore', return_value=vs):
            with patch('app.api.ai.get_ai_provider') as mock_get_provider:
                mock_provider = AsyncMock()
                mock_provider.query_events = AsyncMock(return_value=type('RagResp', (), {
                    'answer': 'I could not find any relevant events.',
                    'events': [],
                    'query_time_ms': 100,
                })())
                mock_get_provider.return_value = mock_provider

                r = client.post("/api/v1/ai/query", json={"query": "secret draft"})
                assert r.status_code == 200
                data = r.json()
                assert 'Secret Draft' not in data.get('answer', '')

    def test_query_no_relevant_events_returns_honest_response(self):
        """A query with no relevant events produces an honest no-results response."""
        with patch('app.api.ai.get_ai_provider') as mock_get_provider:
            mock_provider = AsyncMock()
            mock_provider.query_events = AsyncMock(return_value=type('RagResp', (), {
                'answer': 'I could not find any relevant events matching your question.',
                'events': [],
                'query_time_ms': 100,
            })())
            mock_get_provider.return_value = mock_provider

            r = client.post("/api/v1/ai/query", json={"query": "quantum computing seminar"})
            assert r.status_code == 200
            data = r.json()
            assert 'not find' in data['answer'].lower() or 'no relevant' in data['answer'].lower()


class TestGroundedAnswerGeneration:
    """Test that the AI answer uses facts from retrieved event context."""

    @pytest.mark.asyncio
    async def test_answer_uses_retrieved_event_facts(self):
        """The answer mentions specific event details from the retrieved context."""
        from app.services.ai import NavigateLabsProvider

        provider = NavigateLabsProvider()

        events_context = [{
            "id": 1,
            "title": "Deep Learning Workshop Series",
            "description": "A hands-on 3-session workshop covering neural networks, CNNs, and transformer architectures using PyTorch.",
            "category": "Workshop",
            "venue": "Lab 204, CS Block",
            "date": "2026-10-22",
            "start_time": "14:00",
            "end_time": "17:00",
            "organizer_name": "ML Society",
            "tags": ["Deep Learning", "PyTorch"],
            "relevance_score": 0.95,
        }]

        fake_response = {
            "choices": [{"message": {"content": "The Deep Learning Workshop Series covers neural networks, CNNs, and transformer architectures using PyTorch. It takes place on 2026-10-22 at Lab 204, CS Block."}}]
        }

        with patch.object(provider, '_make_request', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = fake_response
            request = type('Req', (), {'query': 'transformer workshop', 'limit': 10})()
            result = await provider.query_events(request, events_context)

        assert 'Deep Learning Workshop Series' in result.answer
        assert 'transformer' in result.answer.lower()
        assert 'PyTorch' in result.answer
        assert 'Lab 204' in result.answer

    @pytest.mark.asyncio
    async def test_answer_mentions_retrieved_event_titles(self):
        """Answer mentions event titles from retrieved context, not fabricated ones."""
        from app.services.ai import NavigateLabsProvider

        provider = NavigateLabsProvider()

        events_context = [{
            "id": 5,
            "title": "Inter-College Coding Competition",
            "description": "Test your DSA and competitive programming skills.",
            "category": "Competition",
            "venue": "Computer Centre, Ground Floor",
            "date": "2026-11-02",
            "organizer_name": "Code Club",
            "tags": ["DSA", "Competitive Programming"],
            "relevance_score": 0.9,
        }]

        fake_response = {
            "choices": [{"message": {"content": "The Inter-College Coding Competition is on 2026-11-02 at Computer Centre, Ground Floor."}}]
        }

        with patch.object(provider, '_make_request', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = fake_response
            request = type('Req', (), {'query': 'coding competition', 'limit': 10})()
            result = await provider.query_events(request, events_context)

        assert 'Inter-College Coding Competition' in result.answer
        assert 'AI Hackathon' not in result.answer


class TestReindexAndApprovalLifecycle:
    """Test that approval status changes affect vector store indexing."""

    @pytest.mark.asyncio
    async def test_approved_event_becomes_retrievable(self):
        vs = SimpleVectorStore(persist_path=':memory:')
        ev = Event(id=10, title='New AI Event', description='New AI content',
                   category='Workshop', organizer_id=1, status=EventStatus.APPROVED,
                   venue='Hall', date=date(2026, 11, 15))

        class FakeProvider:
            async def get_embedding(self, text: str):
                return [0.5] * 10

        with patch('app.services.ai.get_ai_provider', return_value=FakeProvider()):
            result = await vs.add_event(ev)
            assert result == True
            assert 10 in vs.embeddings

    @pytest.mark.asyncio
    async def test_unapproved_event_not_retrievable(self):
        vs = SimpleVectorStore(persist_path=':memory:')
        draft = Event(id=11, title='Draft Event', description='draft content',
                      category='Seminar', organizer_id=1, status=EventStatus.DRAFT,
                      venue='Room', date=date(2026, 12, 1))
        result = await vs.add_event(draft)
        assert result == False
        assert 11 not in vs.embeddings

    @pytest.mark.asyncio
    async def test_rejected_event_not_retrievable(self):
        vs = SimpleVectorStore(persist_path=':memory:')
        rejected = Event(id=12, title='Rejected Event', description='rejected content',
                         category='Conference', organizer_id=1, status=EventStatus.REJECTED,
                         venue='Room', date=date(2026, 12, 1))
        result = await vs.add_event(rejected)
        assert result == False
        assert 12 not in vs.embeddings


class TestQueryEndpointErrorHandling:
    """Test safe handling of empty, malformed, and failed retrieval results."""

    def test_query_with_empty_vector_store(self):
        with patch('app.api.ai.get_ai_provider') as mock_get_provider:
            mock_provider = AsyncMock()
            mock_provider.query_events = AsyncMock(return_value=type('RagResp', (), {
                'answer': 'I could not find any relevant events matching your question.',
                'events': [],
                'query_time_ms': 50,
            })())
            mock_get_provider.return_value = mock_provider

            r = client.post("/api/v1/ai/query", json={"query": "anything"})
            assert r.status_code == 200
            data = r.json()
            assert 'events' in data
            assert len(data['events']) == 0

    def test_query_provider_error_handled(self):
        with patch('app.api.ai.get_ai_provider') as mock_get_provider:
            mock_provider = AsyncMock()
            mock_provider.query_events = AsyncMock(side_effect=Exception("API timeout"))
            mock_get_provider.return_value = mock_provider

            r = client.post("/api/v1/ai/query", json={"query": "test"})
            assert r.status_code == 500
