"""City Care Clinics - Conversational Intake Agent.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Collects structured clinical history through gentle, single-question UrduLish dialogue:
- Chief complaint, duration, severity scale (1-10)
- Associated symptoms
- Drug allergies & active medicines
- Medical history (Diabetes, Hypertension, Pregnancy)
- Patient identity (Self, Child, Parent)
Outputs validated Pydantic/JSON intake form.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from llm_client import UnifiedLLMClient


class IntakeForm(BaseModel):
    """Structured clinical intake record."""
    patient_identity: Optional[str] = Field(default=None, description="SELF, CHILD, PARENT, or OTHER")
    patient_name: Optional[str] = Field(default=None)
    patient_age: Optional[int] = Field(default=None)
    chief_complaint: Optional[str] = Field(default=None)
    duration: Optional[str] = Field(default=None)
    severity_scale: Optional[int] = Field(default=None, ge=1, le=10)
    associated_symptoms: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    current_medications: List[str] = Field(default_factory=list)
    medical_history: List[str] = Field(default_factory=list)
    is_complete: bool = Field(default=False)
    missing_fields: List[str] = Field(default_factory=list)


INTAKE_SYSTEM_PROMPT = """You are Sitara, the compassionate UrduLish Intake Coordinator at City Care Clinics (Lahore & Islamabad).
Your mission is to collect structured clinical intake information through natural, warm dialogue with utmost cultural adab (use 'Aap', 'Janab', 'Mohtaram').

CRITICAL RULES:
1. ALWAYS ACKNOWLEDGE the patient's concern with genuine warmth and empathy first before asking your next question (e.g. 'Mujhe sun kar afsos hua ke aap ko bukhar hai...').
2. ASK EXACTLY ONE FOCUSED QUESTION AT A TIME. Never ask a long robotic form.
3. If the user mentions multiple pieces of information in one turn (e.g., 'mere 5 saal ke betay ko kal se 102 bukhar hai'), extract all of them:
   - patient_identity (SELF, CHILD, PARENT)
   - chief_complaint
   - duration
   - severity_scale (1-10)
   - associated_symptoms (list)
   - allergies (list)
   - current_medications (list)
   - medical_history (list, e.g. diabetes, BP, pregnancy)
4. Formulate the next single natural conversational UrduLish question for whichever critical field is still missing.
5. NEVER DIAGNOSE and NEVER PRESCRIBE or recommend home remedies.
"""


class IntakeAgent:
    """Production Conversational Intake Specialist Agent."""

    def __init__(self, llm_client: Optional[UnifiedLLMClient] = None):
        self.llm = llm_client or UnifiedLLMClient()

    def process_turn(
        self,
        user_message: str,
        current_state: Optional[IntakeForm] = None
    ) -> Tuple[IntakeForm, str]:
        """Processes a single conversational turn, updates structured state, and returns next single question."""
        if current_state is None:
            current_state = IntakeForm()

        prompt = f"""Existing Intake State:
{current_state.model_dump_json(indent=2)}

New Patient Message:
"{user_message}"

Extract any newly provided clinical fields, update the state, determine which required field is still missing, and generate the NEXT SINGLE QUESTION in polite UrduLish.
Required fields to complete intake:
1. patient_identity (self, child, parent)
2. chief_complaint
3. duration
4. severity_scale (1 to 10)
5. associated_symptoms
6. medical_history_and_allergies

Respond with JSON adhering to:
{{
  "extracted_updates": {{
    "patient_identity": "...",
    "patient_name": "...",
    "patient_age": 30,
    "chief_complaint": "...",
    "duration": "...",
    "severity_scale": 7,
    "associated_symptoms": ["..."],
    "allergies": ["..."],
    "current_medications": ["..."],
    "medical_history": ["..."]
  }},
  "is_complete": false,
  "next_single_question_urdu": "..."
}}
"""
        # Call LLM for extraction
        parsed = self.llm.generate_json(
            prompt=prompt,
            system_prompt=INTAKE_SYSTEM_PROMPT,
            fallback_default={}
        )

        updates = parsed.get("extracted_updates", {})

        # Apply updates to current state
        if updates.get("patient_identity"):
            current_state.patient_identity = updates["patient_identity"].upper()
        if updates.get("patient_name"):
            current_state.patient_name = updates["patient_name"]
        if updates.get("patient_age") is not None:
            current_state.patient_age = updates["patient_age"]
        if updates.get("chief_complaint"):
            current_state.chief_complaint = updates["chief_complaint"]
        if updates.get("duration"):
            current_state.duration = updates["duration"]
        if updates.get("severity_scale") is not None:
            try:
                current_state.severity_scale = int(updates["severity_scale"])
            except Exception:
                pass

        if updates.get("associated_symptoms"):
            for sym in updates["associated_symptoms"]:
                if sym not in current_state.associated_symptoms:
                    current_state.associated_symptoms.append(sym)

        if updates.get("allergies"):
            for alg in updates["allergies"]:
                if alg not in current_state.allergies:
                    current_state.allergies.append(alg)

        if updates.get("current_medications"):
            for med in updates["current_medications"]:
                if med not in current_state.current_medications:
                    current_state.current_medications.append(med)

        if updates.get("medical_history"):
            for h in updates["medical_history"]:
                if h not in current_state.medical_history:
                    current_state.medical_history.append(h)

        # Rule-based field completion check and fallback question generator
        missing = []
        if not current_state.patient_identity:
            missing.append("patient_identity")
        if not current_state.chief_complaint:
            missing.append("chief_complaint")
        if not current_state.duration:
            missing.append("duration")
        if current_state.severity_scale is None:
            missing.append("severity_scale")
        if not current_state.associated_symptoms and len(current_state.associated_symptoms) == 0:
            missing.append("associated_symptoms")

        current_state.missing_fields = missing
        current_state.is_complete = (len(missing) == 0)

        # Generate targeted next single question
        if current_state.is_complete:
            response_urdu = (
                f"Shukriya Janab! Aap ki tamam bunyadi maloomat darj ho chuki hain: "
                f"{current_state.chief_complaint} ({current_state.duration}, shiddat {current_state.severity_scale}/10). "
                f"Main foran aap ki alamaat ka jaiza le kar munasib specialist doctor tajweez karti hoon."
            )
        elif parsed.get("next_single_question_urdu"):
            response_urdu = parsed["next_single_question_urdu"]
        else:
            response_urdu = self._generate_fallback_question(missing)

        return current_state, response_urdu

    def _generate_fallback_question(self, missing_fields: List[str]) -> str:
        """Deterministic question generator if LLM response is empty."""
        if "patient_identity" in missing_fields:
            return "Assalam-o-Alaikum! City Care Clinics mein khushamdeed. Yeh appointment aap apne liye book kar rahe hain ya kisi bache ya walidain ke liye?"
        elif "chief_complaint" in missing_fields:
            return "Aap ko kis takleef ya alamat ka samna hai? Baraye meharbani mukhtasaran batayein."
        elif "duration" in missing_fields:
            return "Yeh takleef kab se hai? Kitne din ya ghante pehle shuru hui?"
        elif "severity_scale" in missing_fields:
            return "Takleef ki shiddat 1 se 10 ke paimanay par kitni hai (jahan 1 halki aur 10 na-qabil-e-bardasht ho)?"
        elif "associated_symptoms" in missing_fields:
            return "Kya is ke sath koi aur alamat jaise ulti, bukhar, saans ki takleef, ya sar dard bhi hai?"
        else:
            return "Kya aap ko pehle se koi bemari (jaise diabetes, high BP, ya pregnancy) hai, aur koi dawai ya allergy?"


if __name__ == "__main__":
    agent = IntakeAgent()
    print("Testing Intake Agent Conversation Flow...")

    # Turn 1
    state, reply1 = agent.process_turn("Assalam-o-Alaikum, mujhe bukhar hai 2 din se.")
    print(f"User: Assalam-o-Alaikum, mujhe bukhar hai 2 din se.")
    print(f"Agent: {reply1}\n")

    # Turn 2
    state, reply2 = agent.process_turn("Apne liye book kar raha hoon, shiddat taqreeban 7/10 hai.", state)
    print(f"User: Apne liye book kar raha hoon, shiddat taqreeban 7/10 hai.")
    print(f"Agent: {reply2}\n")

    # Turn 3
    state, reply3 = agent.process_turn("Saath mein gala kharab hai aur halki khansi hai, sugar ya allergy koi nahi.", state)
    print(f"User: Saath mein gala kharab hai aur halki khansi hai, sugar ya allergy koi nahi.")
    print(f"Agent: {reply3}\n")

    print(f"Intake Completed: {state.is_complete}")
    print(f"Structured Record: {state.model_dump_json(indent=2)}")
