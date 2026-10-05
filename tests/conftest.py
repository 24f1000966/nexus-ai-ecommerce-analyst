"""Point the platform at a throwaway SQLite file before any backend module is imported."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

_tmp = tempfile.mkdtemp(prefix="nexus-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp) / 'platform.db'}"
os.environ.pop("ANTHROPIC_API_KEY", None)   # tests exercise the offline path
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("NEXUS_ENV", None)
