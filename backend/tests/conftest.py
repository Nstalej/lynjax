import os
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Point the whole run at a throwaway data directory before anything imports the
# settings.
#
# Tests override the settings *dependency*, but the app's lifespan resolves its
# own configuration, so a TestClient was opening the developer's real database
# in AppData and writing to it. Nothing corrupted, because the overridden
# dependencies redirect every query, but a test run must not touch a real
# install at all.
os.environ.setdefault("LYNJAX_DATA_DIR", tempfile.mkdtemp(prefix="lynjax-tests-"))
os.environ.setdefault("LYNJAX_LOG_DIR", os.environ["LYNJAX_DATA_DIR"])
