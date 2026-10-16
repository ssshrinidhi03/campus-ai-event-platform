"""Tests for RAG-based semantic search and vector store"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, date

from app.services.vector_store import SimpleVectorStore, EventEmbedding
from app.models.event import Event
from app.models.enums import EventStatus


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
        # Index an approved event, then unpublish it
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
        # Search should not crash and only approved events are in the index
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
        # Missing query
        with pytest.raises(ValueError):
            tool.validate_args({})
        # Empty query
        with pytest.raises(ValueError):
            tool.validate_args({"query": "   "})
        # Valid
        out = tool.validate_args({"query": "AI workshop", "limit": 5, "category": "Workshop"})
        assert out["query"] == "AI workshop"
        assert out["limit"] == 5
        assert out["category"] == "Workshop"
        # Limit clamped
        out = tool.validate_args({"query": "x", "limit": 999})
        assert out["limit"] == 50
        out = tool.validate_args({"query": "x", "limit": 0})
        assert out["limit"] == 1

    @pytest.mark.asyncio
    async def test_tool_execute_only_returns_approved(self):
        from app.services.ai import EventSearchTool
        from app.services.vector_store import SimpleVectorStore
        from app.models.event import Event
        from app.models.enums import EventStatus
        from unittest.mock import Mock, AsyncMock

        vs = SimpleVectorStore(persist_path=':memory:')
        # Mock vector store search to return a fake embedding result
        fake_emb = Mock()
        fake_emb.event_id = 1
        vs.search = AsyncMock(return_value=[(fake_emb, 0.9)])

        # Mock DB: event 1 is APPROVED
        approved = Event(id=1, title='AI Workshop', organizer_id=1, status=EventStatus.APPROVED)
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = approved

        tool = EventSearchTool(vector_store=vs, db_session=db)
        results = await tool.execute({"query": "anything", "limit": 10})
        ids = [r["id"] for r in results]
        assert 1 in ids  # approved event passes DB re-verification

    @pytest.mark.asyncio
    async def test_tool_execute_excludes_unpublished_on_db_reverify(self):
        """DB re-verification excludes events that are no longer approved (stale index)."""
        from app.services.ai import EventSearchTool
        from app.services.vector_store import SimpleVectorStore
        from unittest.mock import Mock, AsyncMock

        vs = SimpleVectorStore(persist_path=':memory:')
        fake_emb = Mock()
        fake_emb.event_id = 5
        vs.search = AsyncMock(return_value=[(fake_emb, 0.9)])

        # Mock DB: event 5 is NOT approved (e.g., now DRAFT) → must be excluded
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None

        tool = EventSearchTool(vector_store=vs, db_session=db)
        results = await tool.execute({"query": "seminar", "limit": 10})
        assert results == []  # unpublished event excluded at authorization boundary
