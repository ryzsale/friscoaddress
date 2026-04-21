from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Annotation
from ..schemas import AnnotationUpdate, BulkUpdate

router = APIRouter(prefix="/annotations", tags=["annotations"])

ALLOWED_FIELDS = {"last_visited", "comments", "status", "ignored"}

def _upsert(db: Session, rid: str, field: str, value):
    ann = db.query(Annotation).filter(Annotation.rid == rid).first()
    if ann is None:
        ann = Annotation(rid=rid)
        db.add(ann)
    setattr(ann, field, value)
    db.commit()


@router.patch("/{rid}")
def update_annotation(
    rid: str,
    body: AnnotationUpdate,
    db: Session = Depends(get_db),
    _: str      = Depends(get_current_user),
):
    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        if field in ALLOWED_FIELDS:
            _upsert(db, rid, field, value)
    return {"ok": True}


@router.post("/bulk")
def bulk_update(
    body: BulkUpdate,
    db: Session = Depends(get_db),
    _: str      = Depends(get_current_user),
):
    if body.field not in {"status", "ignored"}:
        raise HTTPException(400, "Invalid field")
    for rid in body.rids:
        _upsert(db, rid, body.field, body.value)
    return {"ok": True, "updated": len(body.rids)}
