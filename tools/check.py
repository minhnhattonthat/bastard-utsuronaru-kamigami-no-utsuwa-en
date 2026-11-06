"""check.py: the repo's one-command check (tests; lint joins in phase 4+). The pre-commit hook runs this. Exit code = pytest's."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.exit(subprocess.call([sys.executable, "-X", "utf8", "-m", "pytest", "-q", str(ROOT / "tests")], cwd=ROOT))
