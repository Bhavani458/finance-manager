from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.routes import (
    accounts,
    ai_news,
    auth,
    budgets,
    categories,
    investment_types,
    investments,
    reports,
    transactions,
)
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="Finance Manager", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.exception_handler(IntegrityError)
    async def _integrity(_: Request, exc: IntegrityError):
        return JSONResponse(status_code=400, content={"detail": str(exc.orig).splitlines()[0]})

    prefix = "/api/v1"
    app.include_router(auth.router, prefix=prefix)
    app.include_router(accounts.router, prefix=prefix)
    app.include_router(ai_news.router, prefix=prefix)
    app.include_router(transactions.router, prefix=prefix)
    app.include_router(categories.router, prefix=prefix)
    app.include_router(budgets.router, prefix=prefix)
    app.include_router(investment_types.router, prefix=prefix)
    app.include_router(investments.router, prefix=prefix)
    app.include_router(reports.router, prefix=prefix)

    return app


app = create_app()
