import re
import logging
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import get_engine

logger = logging.getLogger("OutputGuard")

def check(agent_response: str) -> tuple[bool, str]:
    """
    Checks the agent response for length and hallucinatory property IDs.
    Returns (is_safe, fallback_message)
    """
    if not agent_response:
        return True, ""
        
    words = agent_response.split()
    if len(words) > 200:
        logger.warning("Output modified: Response exceeded 200 words. Truncating.")
        # We don't block it, just truncate it gracefully
        truncated = " ".join(words[:200]) + "... (mazeed tafseelaat ke liye email check karein)."
        return True, truncated

    # Hallucination check for Property IDs like PROP-123
    prop_matches = re.findall(r"PROP-\d+", agent_response, re.IGNORECASE)
    if prop_matches:
        engine = get_engine()
        with engine.connect() as conn:
            for prop_id in prop_matches:
                res = conn.execute(
                    text("SELECT 1 FROM properties WHERE property_id = :pid"), 
                    {"pid": prop_id.upper()}
                ).fetchone()
                if not res:
                    logger.error(f"Hallucination blocked: Property ID {prop_id} does not exist.")
                    return False, "Maaf kijiye, mujhe is property ki details nahi mil rahin. Main dobara check karta hoon."
                    
    return True, agent_response
