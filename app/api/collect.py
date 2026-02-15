
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import uuid

from app.db.session import get_db
from app.db.models import Run, Video, Template
from app.services.youtube_collector import YouTubeCollector
from app.services.ai_templates import SentimentTemplates

router = APIRouter()

# --- Pydantic Models ---
class CollectRequest(BaseModel):
    keyword: str
    force_refresh: bool = False

class CollectResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    cached: bool
    result: Optional[dict] = None

class VideoObject(BaseModel):
    source: str
    rank: int
    title: str
    channel_name: str
    video_id: str
    video_url: str
    views_raw: str
    views_num: int
    collected_from: str

class TemplateObject(BaseModel):
    template_text: str
    example_1: Optional[str] = None
    example_2: Optional[str] = None

class StatusResponse(BaseModel):
    job_id: uuid.UUID
    keyword: str
    status: str
    hl: str = "id"
    gl: str = "ID"
    search_top: List[VideoObject] = []
    people_also_watched_top: List[VideoObject] = []
    related_fallback_top: List[VideoObject] = []
    templates: List[TemplateObject] = []
    error_message: Optional[str] = None

# --- Background Task ---
async def process_youtube_collection(run_id: uuid.UUID, keyword: str):
    # Create a fresh session for the background task
    from app.db.session import SessionLocal
    background_db = SessionLocal()
    
    try:
        collector = YouTubeCollector(background_db, run_id)
        success = await collector.collect(keyword)
        
        if success:
            # Generate Templates
            templater = SentimentTemplates(background_db, run_id)
            templater.generate()
            
    except Exception as e:
        # Update run status to failed if not already handled
        run = background_db.query(Run).filter(Run.id == run_id).first()
        if run:
            run.status = "failed"
            run.error_message = str(e)
            background_db.commit()
    finally:
        background_db.close()

# --- Endpoints ---

@router.post("/collect/youtube", response_model=CollectResponse)
def collect_youtube(
    request: CollectRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # 1. Check Cache
    if not request.force_refresh:
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        cached_run = db.query(Run).filter(
            Run.keyword == request.keyword,
            Run.status == "success",
            Run.finished_at >= twenty_four_hours_ago
        ).order_by(Run.finished_at.desc()).first()

        if cached_run:
            status_data = _get_status_response(cached_run, db)
            return CollectResponse(
                job_id=cached_run.id,
                status="success",
                cached=True,
                result=status_data.dict()
            )

    # 2. Create New Run
    new_run = Run(
        keyword=request.keyword,
        status="queued"
    )
    db.add(new_run)
    db.commit()
    db.refresh(new_run)

    # 3. Enqueue Background Task
    background_tasks.add_task(process_youtube_collection, new_run.id, request.keyword)

    return CollectResponse(
        job_id=new_run.id,
        status="queued",
        cached=False
    )

@router.get("/status/{job_id}", response_model=StatusResponse)
def get_status(job_id: uuid.UUID, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == job_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return _get_status_response(run, db)

def _get_status_response(run: Run, db: Session) -> StatusResponse:
    # Fetch videos
    videos = db.query(Video).filter(Video.run_id == run.id).all()
    templates = db.query(Template).filter(Template.run_id == run.id).all()

    # Sort videos into categories
    search_top = []
    people_also_watched = []
    related_fallback = []

    for v in videos:
        obj = VideoObject(
            source=v.source_type,
            rank=v.rank,
            title=v.title,
            channel_name=v.channel_name,
            video_id=v.video_id,
            video_url=v.video_url,
            views_raw=v.views_raw,
            views_num=v.views_num if v.views_num else 0,
            collected_from=v.collected_from
        )
        if v.source_type == "search":
            search_top.append(obj)
        elif v.source_type == "people_also_watched":
            people_also_watched.append(obj)
        elif v.source_type == "related_fallback":
            related_fallback.append(obj)

    # Templates
    template_objs = [
        TemplateObject(
            template_text=t.template_text,
            example_1=t.example_1,
            example_2=t.example_2
        ) for t in templates
    ]

    return StatusResponse(
        job_id=run.id,
        keyword=run.keyword,
        status=run.status,
        hl=run.hl,
        gl=run.gl,
        search_top=sorted(search_top, key=lambda x: x.rank),
        people_also_watched_top=sorted(people_also_watched, key=lambda x: x.rank),
        related_fallback_top=sorted(related_fallback, key=lambda x: x.rank),
        templates=template_objs,
        error_message=run.error_message
    )
