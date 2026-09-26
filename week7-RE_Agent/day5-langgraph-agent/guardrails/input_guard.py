import re
import logging

logger = logging.getLogger("InputGuard")

INJECTION_PATTERNS = [
    r"(?i)\bignore\s+(?:all\s+)?(?:previous\s+)?instructions\b",
    r"(?i)\bforget\s+(?:all\s+)?(?:previous\s+)?instructions\b",
    r"(?i)\bjailbreak\b",
    r"(?i)\bsystem\s+prompt\b",
    r"(?i)\bsab\s+bhool\s+jao\b",
    r"(?i)ignore previous",
]

OFF_TOPIC_PATTERNS = [
    r"(?i)\bwrite\s+a\s+poem\b",
    r"(?i)\bwrite\s+code\b",
    r"(?i)\bpython\b",
    r"(?i)\bjavascript\b",
    r"(?i)\bweather\b",
    r"(?i)\bpolitics\b",
    r"(?i)\bwho\s+won\b",
]

def check(user_text: str) -> tuple[bool, str]:
    """
    Checks the user input for prompt injection, extreme length, and off-topic.
    Returns (is_safe, fallback_message)
    """
    if not user_text:
        return True, ""
        
    if len(user_text) > 500:
        logger.warning("Input rejected: Exceeds 500 characters.")
        return False, "Maaf kijiye, aap ka paigham bohat lamba hai. Thora mukhtasar batayein."
        
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, user_text):
            logger.warning(f"Input rejected: Prompt injection detected ({pattern}).")
            return False, "Maaf kijiye, main is tarah ki instructions ko follow nahi kar sakta. Main sirf real estate consultant hoon."
            
    for pattern in OFF_TOPIC_PATTERNS:
        if re.search(pattern, user_text):
            logger.warning(f"Input rejected: Off-topic detected ({pattern}).")
            return False, "Maaf kijiye, main sirf properties aur real estate ke baaray mein baat kar sakta hoon."
            
    return True, ""
