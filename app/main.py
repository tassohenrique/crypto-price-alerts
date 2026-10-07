from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.routers import alerts, health
from app.core.exceptions import AppError

app = FastAPI(
    title="Crypto Price Alerts",
    description="Monitor de preços de criptomoedas com alertas no Telegram",
    version="0.1.0",
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redireciona a raiz para a documentação interativa."""
    return RedirectResponse(url="/docs")


app.include_router(health.router)
app.include_router(alerts.router)
