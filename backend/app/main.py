from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import components


app = FastAPI(
    title="ComponentBox Component Scanner API",
    description="Backend API for accepting ESP32-CAM images and classifying supported electronic components.",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(components.router)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "focus": "component-classification"}
