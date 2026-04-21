from sqlalchemy import Column, String, Integer
from .database import Base

class Annotation(Base):
    __tablename__ = "annotations"
    rid          = Column(String, primary_key=True, index=True)
    last_visited = Column(String, default="")
    comments     = Column(String, default="")
    status       = Column(String, default="")
    ignored      = Column(Integer, default=0)

class ShareToken(Base):
    __tablename__ = "share_tokens"
    token      = Column(String, primary_key=True, index=True)
    filters    = Column(String, nullable=False)
    label      = Column(String, default="")
    created_at = Column(String, nullable=False)
    expires_at = Column(String, nullable=False)
