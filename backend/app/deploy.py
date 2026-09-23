"""Render entry point; the existing app.main/local Docker workflow is unchanged."""
import os
from pathlib import Path

from app.core.config import REPO_ROOT
from app.main import app
from app.web import mount_dashboard

mount_dashboard(app, Path(os.environ.get("FRONTEND_DIST_DIR", REPO_ROOT / "frontend" / "dist")))
