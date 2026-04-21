from pydantic import BaseModel
from typing import Optional, Any

class TokenRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class AnnotationUpdate(BaseModel):
    last_visited: Optional[str] = None
    comments:     Optional[str] = None
    status:       Optional[str] = None
    ignored:      Optional[int] = None

class BulkUpdate(BaseModel):
    rids:  list[str]
    field: str
    value: Any

class OwnerOut(BaseModel):
    rid:            str
    last_name:      str
    first_name:     str
    address:        str
    street:         str
    city_state_zip: str
    zip:            str
    is_muslim:      bool
    status:         str = ""
    last_visited:   str = ""
    comments:       str = ""
    ignored:        bool = False

    model_config = {"from_attributes": True}

class OwnersResponse(BaseModel):
    total:   int
    page:    int
    pages:   int
    records: list[OwnerOut]

class StreetOut(BaseModel):
    street:  str
    zip:     str
    total:   int
    muslim:  int
    visited: int

class DashboardStats(BaseModel):
    total:        int
    muslim:       int
    non_muslim:   int
    visited:      int
    ignored:      int
    status_counts: dict[str, int]
    zip_stats:    list[dict]

class ShareCreate(BaseModel):
    filters: dict
    label:   str = ""
    days:    int = 7

class ShareOut(BaseModel):
    token:      str
    label:      str
    filters:    str
    created_at: str
    expires_at: str
    expired:    bool = False
