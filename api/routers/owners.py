from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..data import get_dataframe
from ..models import Annotation
from ..schemas import OwnersResponse, OwnerOut, DashboardStats

router = APIRouter(prefix="/owners", tags=["owners"])

def _apply_filters(df, q, zip_f, muslim_f, status_f, show_ignored, street_f, db: Session):
    if q:
        mask = (
            df["last_name"].str.contains(q, case=False, na=False) |
            df["first_name"].str.contains(q, case=False, na=False) |
            df["address"].str.contains(q, case=False, na=False)
        )
        df = df[mask]
    if zip_f:
        df = df[df["zip"] == zip_f]
    if street_f:
        df = df[df["street"].str.contains(street_f, case=False, na=False)]
    if muslim_f == "yes":
        df = df[df["is_muslim"]]
    elif muslim_f == "no":
        df = df[~df["is_muslim"]]

    if status_f or not show_ignored:
        ann_map = {a.rid: a for a in db.query(Annotation).all()}
        if status_f:
            df = df[df["rid"].apply(lambda r: (ann_map.get(r) or Annotation()).status == status_f)]
        if not show_ignored:
            df = df[df["rid"].apply(lambda r: not (ann_map.get(r) or Annotation()).ignored)]
    return df

def _enrich(slice_df, db: Session) -> list[OwnerOut]:
    rids    = slice_df["rid"].tolist()
    ann_map = {a.rid: a for a in db.query(Annotation).filter(Annotation.rid.in_(rids)).all()}
    result  = []
    for rec in slice_df.to_dict("records"):
        a = ann_map.get(rec["rid"])
        result.append(OwnerOut(
            **{k: rec[k] for k in ["rid","last_name","first_name","address","street","city_state_zip","zip","is_muslim"]},
            status       = a.status       if a else "",
            last_visited = a.last_visited if a else "",
            comments     = a.comments     if a else "",
            ignored      = bool(a.ignored) if a else False,
        ))
    return result


@router.get("", response_model=OwnersResponse)
def list_owners(
    q:            str  = Query(""),
    zip:          str  = Query(""),
    muslim:       str  = Query(""),
    status:       str  = Query(""),
    street:       str  = Query(""),
    show_ignored: bool = Query(False),
    page:         int  = Query(1, ge=1),
    per_page:     int  = Query(50, ge=1, le=200),
    db: Session        = Depends(get_db),
    _: str             = Depends(get_current_user),
):
    df    = _apply_filters(get_dataframe().copy(), q, zip, muslim, status, show_ignored, street, db)
    total = len(df)
    pages = max(1, (total + per_page - 1) // per_page)
    page  = min(page, pages)
    start = (page - 1) * per_page
    return OwnersResponse(total=total, page=page, pages=pages,
                          records=_enrich(df.iloc[start:start+per_page], db))


@router.get("/zips", tags=["owners"])
def list_zips(_: str = Depends(get_current_user)):
    return sorted(get_dataframe()["zip"].dropna().unique().tolist())


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    df         = get_dataframe()
    total      = len(df)
    muslim     = int(df["is_muslim"].sum())
    all_ann    = db.query(Annotation).all()
    status_counts = {"Muslim": 0, "Non-Muslim": 0, "Not to Visit": 0}
    visited = ignored = 0
    for a in all_ann:
        if a.status in status_counts:
            status_counts[a.status] += 1
        if a.last_visited:
            visited += 1
        if a.ignored:
            ignored += 1
    by_zip = (df.groupby("zip")["is_muslim"]
                .agg(total="count", muslim="sum")
                .reset_index()
                .sort_values("total", ascending=False))
    return DashboardStats(
        total=total, muslim=muslim, non_muslim=total-muslim,
        visited=visited, ignored=ignored,
        status_counts=status_counts,
        zip_stats=by_zip.to_dict("records"),
    )
