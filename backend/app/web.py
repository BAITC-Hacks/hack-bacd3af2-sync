"""Serve the built dashboard alongside the API in the single-service deployment."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def mount_dashboard(app: FastAPI, directory: Path) -> None:
    index = directory / "index.html"
    if not index.is_file():
        raise RuntimeError(f"Frontend build missing: {index}")

    async def dashboard() -> FileResponse:
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    # Explicit SPA routes support refresh without turning unknown API paths into HTML.
    for path in ("/", "/forecast", "/about"):
        app.add_api_route(path, dashboard, methods=["GET", "HEAD"], include_in_schema=False)
    # API routes are registered first. StaticFiles protects against path traversal.
    app.mount("/", StaticFiles(directory=directory), name="dashboard-assets")
