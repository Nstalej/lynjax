"""Serving the compiled frontend from inside the package.

The single-container decision lives here. Lynjax ships the built React bundle as
package data and FastAPI serves it, so the same artefact works three ways:

* ``pipx install lynjax`` then ``lynjax serve`` on a laptop;
* ``docker run`` for a server;
* ``lynjax audit`` headless, with no UI involved.

NetVault ran two containers with nginx proxying to the backend, which meant a
second image to build, a proxy config to keep in sync, and CORS between two
origins. One process on one port removes all three problems.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

logger = logging.getLogger("lynjax.web")

#: Where `npm run build` output is copied at package build time.
BUNDLED_WEB_DIR = Path(__file__).parent / "web"


def find_web_root() -> Path | None:
    """Locate the compiled frontend, if there is one.

    Checks the bundled copy first, then the development tree, so `npm run dev`
    output is picked up without reinstalling the package.
    """
    if (BUNDLED_WEB_DIR / "index.html").is_file():
        return BUNDLED_WEB_DIR

    dev_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if (dev_dist / "index.html").is_file():
        return dev_dist

    return None


class SinglePageApp(StaticFiles):
    """Static files that fall back to index.html for client-side routes.

    A React router owns paths like ``/devices/3``. Without this, a browser
    refresh on one of those asks the server for a file that does not exist and
    gets a 404 instead of the app.
    """

    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code == 404:
            return await super().get_response("index.html", scope)
        return response


def mount_frontend(app: FastAPI) -> bool:
    """Mount the UI at ``/``. Returns False when no build is present.

    A missing bundle is not an error: the API is useful on its own, and
    ``lynjax audit`` never touches the UI.
    """
    web_root = find_web_root()

    if web_root is None:
        logger.info(
            "No compiled frontend found. The API is available; run "
            "`npm run build` in frontend/ to serve the UI."
        )

        @app.get("/", include_in_schema=False)
        async def _no_ui() -> JSONResponse:
            return JSONResponse(
                {
                    "detail": (
                        "The Lynjax API is running, but no compiled frontend was "
                        "found. Build it with `npm run build` in frontend/, or use "
                        "the API directly at /docs."
                    )
                }
            )

        return False

    app.mount("/", SinglePageApp(directory=web_root, html=True), name="web")
    logger.info("Serving the frontend from %s", web_root)
    return True
