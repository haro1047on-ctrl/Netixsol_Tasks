"""Bootstrap the intent training log WITHOUT using any Vapi minutes.

This runs realistic sample utterances straight through the real
`intent_detection_node()` — the exact same code path a live call uses — so
the resulting training log is indistinguishable from real call data. The
only thing skipped is the phone/voice layer (Vapi + Deepgram), which is
where your minutes actually get consumed.

Why this is legitimate (not "fake data"):
    The rule engine (_classify_intent) still does the real classification
    work here — nothing about the label is invented by this script. This
    is the same trick agent_cli.py already uses for local testing; this
    script just automates feeding it many varied phrasings quickly instead
    of you typing them one at a time.

Usage:
    python -m learning.seed_training_data
    python -m learning.seed_training_data --count 60   # add more/fewer

You can safely re-run this — it just appends more examples. Mix in your
own real call data too (that happens automatically once you deploy); this
script is only meant to get you past the 40-example minimum quickly so you
can see the trainer actually run, not to be your only source of data
forever. Replace/extend SAMPLE_UTTERANCES below with phrasing patterns your
actual callers use for the best results.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from state import create_initial_state
from nodes.intent_detection_node import intent_detection_node
from learning.dataset import dataset_stats

# Realistic (Roman Urdu / Urdu / English mixed, matching your actual caller
# base) phrasings per intent. Add your own — the more varied the phrasing,
# the better the eventual model generalizes.
SAMPLE_UTTERANCES = {
    "greeting": [
        "assalam o alaikum kaise hain aap",
        "hello good morning",
        "hi wanted to say salam",
        "salam kaise ho aap",
        "hey there how are you",
        "aoa, sab khairiyat",
    ],
    "recommendation": [
        "mujhe lahore mein ghar chahiye",
        "flat dikhayein islamabad mein",
        "3 crore budget hai koi option",
        "mujhe 2 bedroom apartment chahiye DHA mein",
        "karachi mein ghar dikhayein",
        "budget 5 crore hai plot chahiye",
        "kuch acha sa ghar bata dein",
        "gulberg mein koi property hai",
    ],
    "rag": [
        "kya aap loan approval process bata sakte hain",
        "registry ke documents kya chahiye",
        "property transfer ka process kya hai",
        "school aur hospital kitni door hain",
        "tax aur fees kitni lagti hain",
        "noc approval ka process kya hai",
        "mortgage kaise milta hai",
        "stamp duty kitni hai",
    ],
    "booking": [
        "visit book karna hai kal",
        "appointment schedule karo",
        "meeting fix kar dein please",
        "kal subah visit rakh dein",
        "property dekhne ke liye time chahiye",
        "mujhe appointment book karni hai",
    ],
    "rescheduling": [
        "meeting ka time change karna hai",
        "appointment ko reschedule kar dein",
        "kal ki booking agay badha dein",
        "time badal dein please visit ka",
    ],
    "cancellation": [
        "meeting cancel kar dein",
        "appointment cancel karni hai",
        "visit cancel kar do please",
        "mujhe booking cancel karni hai",
    ],
    "email": [
        "email bhej dein details ke sath",
        "mujhe email par bhej dein",
        "email pe details send kar dein",
    ],
    "goodbye": [
        "theek hai shukriya khuda hafiz",
        "bye take care",
        "ok thanks bye",
        "shukriya allah hafiz",
    ],
}


def seed(count: int = 40) -> None:
    intents = list(SAMPLE_UTTERANCES.keys())
    produced = 0
    session_counter = 0

    while produced < count:
        intent = intents[produced % len(intents)]
        text = random.choice(SAMPLE_UTTERANCES[intent])

        session_counter += 1
        state = create_initial_state(session_id=f"seed_session_{session_counter}")
        state["raw_user_input"] = text
        intent_detection_node(state)  # this is what actually logs the example

        produced += 1

    print(f"[seed_training_data] Ran {produced} sample turns through the real intent node.")
    print(f"[seed_training_data] Dataset now: {dataset_stats()}")
    print("[seed_training_data] Next: python -m learning.train_intent_classifier")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=40, help="How many sample turns to run (default 40).")
    args = parser.parse_args()
    seed(args.count)
