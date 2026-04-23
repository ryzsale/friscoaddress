"""Frisco Address — FastAPI enterprise backend."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .auth import verify_password, create_token, USERS
from .database import init_db
from .schemas import TokenRequest, TokenResponse
from .routers import owners, annotations, streets, export, shares, zipcodes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log.info("Database initialized")
    from .data import get_dataframe
    df = get_dataframe()
    log.info(f"Loaded {len(df):,} property records")
    yield


app = FastAPI(
    title="Frisco Address Admin API",
    description="Enterprise API for Frisco property owner management",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(owners.router)
app.include_router(annotations.router)
app.include_router(streets.router)
app.include_router(export.router)
app.include_router(shares.router)
app.include_router(zipcodes.router)


@app.post("/auth/token", response_model=TokenResponse, tags=["auth"])
def login(body: TokenRequest):
    hashed = USERS.get(body.username)
    if not hashed or not verify_password(body.password, hashed):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_token(body.username))


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}
