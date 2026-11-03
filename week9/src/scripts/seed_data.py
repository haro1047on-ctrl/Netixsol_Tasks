"""City Care Clinics - Seed Data Wrapper.

Allows executing the database seeder directly from week9/src/scripts/seed_data.py.
"""
import sys
import importlib.util
from pathlib import Path

# Setup path resolution
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parents[2]
DAY2_SCRIPTS = ROOT_DIR / "week9" / "Day2" / "src" / "scripts" / "seed_data.py"

spec = importlib.util.spec_from_file_location("day2_seed_data", str(DAY2_SCRIPTS))
day2_module = importlib.util.module_from_spec(spec)
sys.modules["day2_seed_data"] = day2_module
spec.loader.exec_module(day2_module)

if __name__ == "__main__":
    day2_module.seed_database()
