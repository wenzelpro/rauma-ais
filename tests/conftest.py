import sys
import pathlib
import os

# Ensure project root is on sys.path for module imports
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Use in-memory SQLite database for tests
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
