from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..data import get_dataframe
from ..models import Annotation
from ..schemas import StreetOut

router = APIRouter(prefix="/streets", tags=["streets"])


@router.get("", response_model=list[StreetOut])
def list_streets(
    zip:     str = Query(""),
    muslim:  str = Query("yes"),
    q:       str = Query(""),
    db: Session  = Depends(get_db),
    _: str       = Depends(get_current_user),
):
    df = get_dataframe().copy()
    if zip:
        df = df[df["zip"] == zip]
    if muslim == "yes":
        df = df[df["is_muslim"]]
    elif muslim == "no":
        df = df[~df["is_muslim"]]

    ann_map     = {a.rid: a for a in db.query(Annotation).all()}
    visited_set = {rid for rid, a in ann_map.items() if a.last_visited}
    ignored_set = {rid for rid, a in ann_map.items() if a.ignored}

    df = df[~df["rid"].isin(ignored_set)]
    if q:
        df = df[df["street"].str.contains(q, case=False, na=False)]

    grouped = (df.groupby(["street","zip"])
                 .agg(total=("rid","count"), muslim=("is_muslim","sum"), rids=("rid",list))
                 .reset_index())
    grouped["visited"] = grouped["rids"].apply(lambda rs: sum(1 for r in rs if r in visited_set))
    grouped = grouped.sort_values("muslim", ascending=False)

    return [
        StreetOut(street=r.street, zip=r.zip, total=int(r.total),
                  muslim=int(r.muslim), visited=int(r.visited))
        for r in grouped.itertuples()
    ]


@router.get("/{street}/route")
def street_route(
    street: str,
    zip:    str = Query(""),
    db: Session = Depends(get_db),
    _: str      = Depends(get_current_user),
):
    from urllib.parse import quote_plus
    df = get_dataframe()
    df = df[df["is_muslim"] & (df["street"] == street.upper())]
    if zip:
        df = df[df["zip"] == zip]

    ann_map     = {a.rid: a for a in db.query(Annotation).all()}
    ignored_set = {rid for rid, a in ann_map.items() if a.ignored}
    df = df[~df["rid"].isin(ignored_set)]

    addresses = [f"{r['address']}, {r['city_state_zip']}" for r in df.head(10).to_dict("records")]
    if not addresses:
        return {"url": None}
    url = "https://www.google.com/maps/dir/" + "/".join(quote_plus(a) for a in addresses) + "/"
    return {"url": url, "stops": len(addresses)}
