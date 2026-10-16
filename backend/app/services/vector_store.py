"""Vector Store Service for RAG-based Semantic Search"""
import logging, math, json, os, hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from app.models.event import Event
from app.models.enums import EventStatus
logger = logging.getLogger(__name__)

@dataclass
class EventEmbedding:
    event_id: int
    title: str
    description: str
    organization: str
    category: str
    venue: str
    date: Optional[str]
    tags: List[str]
    embedding: List[float]
    metadata: Dict[str, Any]
    updated_at: datetime

class SimpleVectorStore:
    def __init__(self, persist_path: Optional[str]=None):
        if persist_path is None:
            persist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data','embeddings.json')
        self.persist_path = persist_path
        self._ensure_data_dir()
        self.embeddings: Dict[int,EventEmbedding]={}
        self._load()
    def _ensure_data_dir(self):
        if self.persist_path == ':memory:':
            return
        d=os.path.dirname(self.persist_path)
        if d: os.makedirs(d, exist_ok=True)
    def _load(self):
        if self.persist_path == ':memory:':
            self.embeddings={}; return
        try:
            if os.path.exists(self.persist_path):
                with open(self.persist_path,'r',encoding='utf-8') as f:
                    data = json.load(f)
                for item in data:
                    item['updated_at'] = datetime.fromisoformat(item['updated_at'])
                    self.embeddings[item['event_id']] = EventEmbedding(**item)
        except Exception as e:
            logger.warning(f'load fail {e}'); self.embeddings={}
    def _save(self):
        if self.persist_path == ':memory:':
            return
        try:
            data=[]
            for emb in self.embeddings.values():
                it=asdict(emb); it['updated_at']=emb.updated_at.isoformat(); data.append(it)
            with open(self.persist_path,'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
        except Exception as e: logger.error(f'save fail {e}')
    def _cosine(self,a,b):
        if len(a)!=len(b): m=min(len(a),len(b)); a,b=a[:m],b[:m]
        d=sum(x*y for x,y in zip(a,b)); n1=math.sqrt(sum(x*x for x in a)); n2=math.sqrt(sum(y*y for y in b))
        if n1==0 or n2==0: return 0.0
        return d/(n1*n2)
    def _hash(self,t):
        h=hashlib.sha256(t.encode('utf-8')).hexdigest(); v=[]
        for i in range(0,min(len(h),1536),4): v.append(((int(h[i:i+4],16)/(16**4-1))-0.5)*2)
        while len(v)<384: v.append(0.0)
        return v[:384]
    async def _gen(self,t):
        try:
            from app.services.ai import get_ai_provider
            p=get_ai_provider()
            if hasattr(p,'get_embedding'): return await p.get_embedding(t)
            if hasattr(p,'embed'): return await p.embed(t)
        except Exception: pass
        return self._hash(t)
    def _text(self,e):
        p=[]
        if e.title: p.append(f'Title:{e.title}')
        if e.description: p.append(f'Desc:{e.description}')
        if e.organization: p.append(f'Org:{e.organization}')
        if e.category: p.append(f'Cat:{e.category}')
        if e.venue: p.append(f'Venue:{e.venue}')
        if e.tags: p.append(f'Tags:{e.tags}')
        if e.eligibility: p.append(f'Elig:{e.eligibility}')
        if e.speaker_info: p.append(f'Spk:{e.speaker_info}')
        if e.date: p.append(f'Date:{e.date.isoformat()}')
        return ' '.join(p)
    async def add_event(self,e):
        if e.status!=EventStatus.APPROVED:
            if e.id in self.embeddings:
                self.remove_event(e.id)
            return False
        em=await self._gen(self._text(e)); tags=e.tags.split(',') if e.tags else []
        self.embeddings[e.id]=EventEmbedding(event_id=e.id,title=e.title or '',description=e.description or '',organization=e.organization or '',category=e.category or '',venue=e.venue or '',date=e.date.isoformat() if e.date else None,tags=[x.strip() for x in tags if x.strip()],embedding=em,metadata={'status':e.status.value if hasattr(e.status,'value') else str(e.status),'organizer_id':e.organizer_id},updated_at=datetime.utcnow())
        self._save(); return True
    def remove_event(self,i):
        if i in self.embeddings:
            del self.embeddings[i]; self._save(); return True
        return False
    async def update_event(self,e): return await self.add_event(e)
    async def reindex_all(self,db):
        res={'indexed':0,'skipped':0,'removed':0}
        ap=db.query(Event).filter(Event.status==EventStatus.APPROVED).all(); ids=set(x.id for x in ap)
        for eid in list(self.embeddings):
            if eid not in ids: self.remove_event(eid); res['removed']+=1
        for e in ap:
            if await self.add_event(e): res['indexed']+=1
            else: res['skipped']+=1
        return res
    async def search(self,q,limit=10,filters=None):
        if not q or not self.embeddings: return []
        qe=await self._gen(q); out=[]
        for emb in self.embeddings.values():
            if filters and filters.get('category'):
                if str(emb.category).lower()!=str(filters['category']).lower(): continue
            s=self._cosine(qe,emb.embedding)
            if s>0.20: out.append((emb,s))
        out.sort(key=lambda x:x[1],reverse=True); return out[:limit]
    def get_stats(self): return {'total_embeddings':len(self.embeddings),'persist_path':self.persist_path}
