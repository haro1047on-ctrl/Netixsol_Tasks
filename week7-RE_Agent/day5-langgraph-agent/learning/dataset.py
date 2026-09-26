import logging
import pandas as pd
from sqlalchemy import text
import sys
from pathlib import Path

# Add parent dir to path so we can import config
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import get_engine

logger = logging.getLogger("LearningDataset")

def log_training_example(user_text: str, true_intent: str, session_id: str, confidence: float = 1.0) -> None:
    """Log a single training example to the DB."""
    if not user_text.strip():
        return
        
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO training_data (user_message, intent, confidence, session_id) VALUES (:msg, :intent, :conf, :sid)"),
                {"msg": user_text, "intent": true_intent, "conf": confidence, "sid": session_id}
            )
    except Exception as e:
        logger.error(f"Failed to log training example: {e}")

def log_full_conversation(session_id: str, turns: list) -> None:
    """
    Log a full conversation to the DB.
    turns: list of dicts with 'user_message', 'agent_message', 'intent'
    """
    try:
        engine = get_engine()
        with engine.begin() as conn:
            for idx, turn in enumerate(turns):
                conn.execute(
                    text("""INSERT INTO conversations 
                            (session_id, turn_index, user_message, agent_message, intent) 
                            VALUES (:sid, :idx, :umsg, :amsg, :intent)"""),
                    {
                        "sid": session_id,
                        "idx": idx,
                        "umsg": turn.get("user_message", ""),
                        "amsg": turn.get("agent_message", ""),
                        "intent": turn.get("intent", "")
                    }
                )
    except Exception as e:
        logger.error(f"Failed to log full conversation: {e}")

def get_training_data() -> pd.DataFrame:
    """Fetch training data from the DB as a pandas DataFrame."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            df = pd.read_sql_query(text("SELECT user_message, intent FROM training_data WHERE user_message != '' AND intent != ''"), conn)
            return df
    except Exception as e:
        logger.error(f"Failed to fetch training data: {e}")
        return pd.DataFrame(columns=["user_message", "intent"])
