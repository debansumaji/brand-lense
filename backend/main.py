import logging
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from comparison import build_result
from ai_agent import extract_product
from errors import AppError
from models import AnalyzeRequest, AnalyzeResponse, Source
from scraper import clean_manual_text, fetch_product_text, validate_url

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def _allowed_origins() -> list[str]:
    configured = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app = FastAPI(title="BeforeYouBuy API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
DEMO_PAGES_DIR = Path(__file__).resolve().parent / "demo_pages"
app.mount("/demo", StaticFiles(directory=str(DEMO_PAGES_DIR)), name="demo")


def _source_mode(url: str) -> str:
    parsed = urlparse(url)
    if (parsed.hostname or "").lower() in {"localhost", "127.0.0.1"} and parsed.path.startswith("/demo/"):
        return "demo"
    return "scraped"


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    del request
    return JSONResponse(status_code=exc.status, content={"detail": {"code": exc.code, "message": exc.message}})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    del request
    return JSONResponse(status_code=422, content={"detail": {"code": "INVALID_BODY", "message": "Request body failed validation."}})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    del request
    return JSONResponse(status_code=500, content={"detail": {"code": "INTERNAL_ERROR", "message": str(exc)}})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    if payload.page_text:
        page_text = clean_manual_text(payload.page_text)
        if not page_text:
            raise AppError("NO_PRODUCT_CONTENT", "Please paste some product page text to continue.")
        product = extract_product(page_text)
        source = Source(mode="manual_text", chars_used=len(page_text))
    else:
        validate_url(payload.url)
        page_text, chars_used = fetch_product_text(payload.url)
        product = extract_product(page_text)
        source = Source(mode=_source_mode(payload.url), chars_used=chars_used)
    return build_result(payload.requirements, product, source)

