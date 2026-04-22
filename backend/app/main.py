import logging
from contextlib import asynccontextmanager

from curl_cffi.requests import AsyncSession
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.availability import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)
logging.getLogger("curl_cffi").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — initialising HTTP client")
    app.state.http_client = AsyncSession(
        impersonate="chrome124",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/135.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nycgovparks.org/permits/field-and-court/map",
        },
        allow_redirects=True,
    )
    yield
    logger.info("Shutting down — closing HTTP client")
    await app.state.http_client.close()


app = FastAPI(
    title="NYC Parks Field Availability API",
    description=(
        "Search available athletic fields across NYC Parks.\n\n"
        "Data source: [NYC Parks Field & Court Permits]"
        "(https://www.nycgovparks.org/permits/field-and-court/map)"
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:4173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok"}
