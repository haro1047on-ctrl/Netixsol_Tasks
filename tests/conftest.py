"""City Care Clinics - Pytest Configuration and Global Fixtures.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Sets up unified sys.path resolution across Day 1 to Day 5, database engine,
and FastAPI TestClient instances.
"""
import os
import sys
import pytest

# Ensure all src directories are on sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEEK9_DIR = os.path.join(ROOT_DIR, "week9")

for day in ["Day1", "Day2", "Day3", "Day4", "Day5"]:
    src_path = os.path.join(WEEK9_DIR, day, "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

from db_models import init_db, get_db_engine
from services.auth_service import get_auth_service
from services.email_service import get_email_service
from services.reminder_service import get_reminder_service
from scheduling_agent import SchedulingAgent
from triage_agent import TriageAgent
from hitl_manager import get_hitl_manager
from supervisor_graph import ClinicSupervisorOrchestrator
from api_server import app
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Initializes database schema and seeds default accounts once per test session."""
    engine = get_db_engine()
    init_db(engine)
    auth = get_auth_service()
    auth.seed_default_users()
    yield


@pytest.fixture(scope="session")
def client():
    """Returns FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_service():
    return get_auth_service()


@pytest.fixture
def scheduling_agent_fixture():
    return SchedulingAgent()


@pytest.fixture
def triage_agent_fixture():
    return TriageAgent()


@pytest.fixture
def hitl_manager_fixture():
    return get_hitl_manager()


@pytest.fixture
def email_service_fixture():
    return get_email_service()


@pytest.fixture
def reminder_service_fixture():
    return get_reminder_service()


@pytest.fixture
def orchestrator_fixture():
    return ClinicSupervisorOrchestrator(fast_eval_mode=True)
