"""City Care Clinics - Deterministic Triage & Red-Flag Safety Engine.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Zero-latency pre-LLM emergency screening and urgency classification in UrduLish and English.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple
from clinical_state import ClinicalSpecialty, TriageAssessment, TriageLevel


# 1. Deterministic Red-Flag Dictionaries (UrduLish + English terms)
RED_FLAG_PATTERNS: Dict[str, Dict[str, Any]] = {
    "CARDIOVASCULAR": {
        "patterns": [
            r"(?:seene|seenay|seena|chhati)\s+mein\s+(?:\w+\s+){0,3}(?:dard|dabao|pressure|bojh|jalan)",
            r"chest\s+(?:pain|pressure|tightness|discomfort)",
            r"(?:baayein|bayein|ultay|ulte)\s+(?:baazu|bazu)",
            r"(?:baazu|bazu)\s+mein\s+(?:phail|dard|ja\s+raha|khichaao|khichao)",
            r"jabray\s+mein\s+dard",
            r"jaw\s+pain",
            r"thanday?\s+paseen",
            r"cold\s+sweats",
            r"angina",
            r"dil\s+ki\s+dharkan\s+tez\s+behoshi",
            r"palpitations\s+with\s+dizziness"
        ],
        "rationale": "High clinical suspicion of Acute Coronary Syndrome (Myocardial Infarction)."
    },
    "RESPIRATORY": {
        "patterns": [
            r"saans\s+(?:lene\s+mein\s+)?(?:(?:\w+)\s+)?(?:dushwari|takleef|mushkil|rukn|band)",
            r"saans\s+phool\s+rahi\s+hai\s+bohot",
            r"severe\s+shortness\s+of\s+breath",
            r"hont\s+neelay",
            r"blue\s+lips",
            r"cyanosis",
            r"stridor",
            r"choking",
            r"dam\s+ghut\s+raha",
            r"inability\s+to\s+speak\s+full\s+sentences"
        ],
        "rationale": "Acute respiratory compromise / potential airway compromise or pulmonary embolism."
    },
    "NEUROLOGICAL_FAST": {
        "patterns": [
            r"munh\s+tedha",
            r"facial\s+droop",
            r"face\s+droop",
            r"baazu\s+kamzor",
            r"arm\s+weakness",
            r"taang\s+kamzor",
            r"leg\s+paralysis",
            r"sunn\s+ho\s+gaya",
            r"paralyz",
            r"sunn\s+aur\s+paralyzed",
            r"aawaz\s+ladkhara",
            r"slurred\s+speech",
            r"bol\s+nahi\s+pa\s+raha",
            r"behosh",
            r"unconscious",
            r"loss\s+of\s+consciousness",
            r"mirgi\s+ka\s+daura",
            r"active\s+seizure",
            r"worst\s+headache\s+of\s+life",
            r"sab\s+se\s+shadeed\s+sar\s+dard",
            r"thunderclap\s+headache"
        ],
        "rationale": "Suspected acute stroke (FAST positive), status epilepticus, or intracranial hemorrhage."
    },
    "HEMORRHAGIC_TRAUMA": {
        "patterns": [
            r"khoon\s+nahi\s+ruk",
            r"uncontrolled\s+bleeding",
            r"heavy\s+bleeding",
            r"balgham\s+mein\s+(?:(?:\w+)\s+)?khoon",
            r"coughing\s+(?:up\s+)?blood",
            r"hemoptysis",
            r"khoon(?:i|\s+ki)?\s+ulti",
            r"vomiting\s+blood",
            r"hematemesis",
            r"kaala\s+pakhana",
            r"black\s+stool",
            r"shadeed\s+car\s+accident",
            r"severe\s+head\s+injury",
            r"sar\s+par\s+shadeed\s+chot"
        ],
        "rationale": "Active significant hemorrhage or major physical trauma."
    },
    "PEDIATRIC_DANGER": {
        "patterns": [
            r"bach[aei]\s+doodh\s+nahi\s+pee",
            r"unable\s+to\s+(?:drink|feed)",
            r"bach[aei]\s+bilkul\s+sust",
            r"extreme\s+lethargy",
            r"pasliyan\s+chal\s+rahi",
            r"chest\s+indrawing",
            r"grunting",
            r"blue\s+baby"
        ],
        "rationale": "Severe pediatric danger signs indicating potential sepsis or acute pneumonia."
    },
    "PSYCHIATRIC_CRISIS": {
        "patterns": [
            r"khudkushi",
            r"suicide",
            r"jaan\s+lena\s+chahta",
            r"apne\s+aap\s+ko\s+khatam",
            r"want\s+to\s+end\s+my\s+life",
            r"kill\s+myself",
            r"self\s+harm"
        ],
        "rationale": "Active suicidal ideation or imminent self-harm risk."
    },
    "OBSTETRIC_EMERGENCY": {
        "patterns": [
            r"hamal\s+mein\s+khoon",
            r"pregnancy\s+bleeding",
            r"vaginal\s+bleeding\s+(?:during\s+)?pregnancy",
            r"shadeed\s+pet\s+dard\s+hamal",
            r"severe\s+abdominal\s+pain\s+pregnancy",
            r"aankhon\s+ke\s+aage\s+andhera\s+hamal",
            r"flashing\s+lights\s+blood\s+pressure\s+pregnancy"
        ],
        "rationale": "Suspected placental abruption, ectopic rupture, or severe pre-eclampsia."
    },
    "TOXIC_INGESTION_OR_OVERDOSE": {
        "patterns": [
            r"overdose",
            r"(?:\d+\s+)?(?:tablets?|goli|goliyan)\s+(?:aik\s+sath|at\s+once)",
            r"10\s+panadol",
            r"5000mg|4000mg",
            r"zehar",
            r"poison",
            r"toxic\s+ingestion"
        ],
        "rationale": "Potential toxic drug overdose or acute ingestion risk requiring immediate emergency evaluation."
    }
}

# 2. Standard UrduLish Emergency Response Message
EMERGENCY_SCRIPT_URDULISH = (
    "🚨 FORI TIBBI IMDAD KI ZAROORAT HAI / EMERGENCY MEDICAL ALERT 🚨\n\n"
    "Aap ki batai hui alamaat (jaise seene mein dard, saans ki takleef, ya behoshi) nihayat sanjeeda hain "
    "aur fori emergency ilaaj ki talabgaar hain.\n\n"
    "Baraye meharbani bila-takheer yeh karein:\n"
    "1. FORAN 1122 (Rescue 1122) par call karein ya qareebi hospital ki Emergency jayein.\n"
    "2. Gaari khud drive na karein; kisi ko madad ke liye sath lein.\n"
    "3. City Care Clinics aik outpatient clinic hai jahan emergency ICU/OT suhoolat nahi hoti.\n\n"
    "Lahore: Services Hospital, Mayo Hospital, ya Doctors Hospital Emergency.\n"
    "Islamabad: PIMS Hospital ya Shifa International Emergency.\n"
    "Allah aap ko sehat ata farmaye."
)

PEDIATRIC_EMERGENCY_SCRIPT = (
    "🚨 BACHAY KI TIBBI EMERGENCY / PEDIATRIC ALERT 🚨\n\n"
    "Mohtaram Walid / Walida:\n"
    "Chotay bachon mein shadeed bukhar, doodh na peena, ya pasliyan chalna fori emergency ki nishani hai.\n\n"
    "Baraye meharbani foran bachay ko qareebi Children's Hospital Emergency (maslan Children Hospital Lahore "
    "ya PIMS Children Ward Islamabad) le kar jayein. Outpatient clinic ka intizar hargiz na karein!"
)


# 3. Specialty Mapping Rules
SPECIALTY_KEYWORDS: Dict[ClinicalSpecialty, List[str]] = {
    ClinicalSpecialty.CARDIOLOGY: [
        "heart", "palpitations", "blood pressure", "bp", "dil ki", "dil", "bp check",
        "cholesterol", "breathless on walking", "chest tightness mild", "170/100", "hypertension"
    ],
    ClinicalSpecialty.PAEDIATRICS: [
        "bacha", "bachay", "bache", "bachi", "baby", "child", "infant", "toddler",
        "vaccination", "bachon ka doctor", "teething", "betay", "beti"
    ],
    ClinicalSpecialty.GYNAECOLOGY: [
        "pregnancy", "hamal", "periods", "mahwaari", "haiz", "pcos",
        "ultrasound pregnancy", "leukorrhea", "gynae", "ladies doctor", "delivery", "gynaecologist", "trimester"
    ],
    ClinicalSpecialty.DERMATOLOGY: [
        "skin", "rash", "jild", "kharish", "acne", "daanay", "chehray",
        "hair fall", "baal girna", "eczema", "fungal", "skin allergy", "khushk"
    ],
    ClinicalSpecialty.ENT: [
        "ear", "kaan", "ear pain", "kaan mein dard", "kaan behna", "gala", "gala kharab", "sore throat",
        "tonsils", "naak", "naak band", "sinus", "hearing loss", "sunai", "wax", "mail"
    ],
    ClinicalSpecialty.GENERAL_MEDICINE: [
        "fever", "bukhar", "khansi", "cough", "flu", "nazla",
        "sugar", "diabetes", "headache", "sar dard", "pet dard", "abdominal pain",
        "vomiting", "ulti", "dast", "diarrhea", "weakness", "kamzori", "ghutno", "multivitamin", "elderly"
    ]
}


class TriageEngine:
    """Production Triage & Safety Classifier."""

    def __init__(self):
        self._compile_regexes()

    def _compile_regexes(self):
        """Pre-compiles regex patterns for high-throughput scanning."""
        self.compiled_red_flags: List[Tuple[str, re.Pattern, str]] = []
        for cat_name, data in RED_FLAG_PATTERNS.items():
            for pat_str in data["patterns"]:
                pat = re.compile(pat_str, re.IGNORECASE)
                self.compiled_red_flags.append((cat_name, pat, data["rationale"]))

    def evaluate(
        self,
        message: str,
        patient_age: Optional[int] = None,
        is_pediatric: bool = False,
        reported_temp_f: Optional[float] = None
    ) -> TriageAssessment:
        """Evaluates patient text against red-flags, pediatric cutoffs, and specialty maps."""
        clean_text = message.strip().lower()

        # Step 1: Check Neonatal / Pediatric Specific Red-Flags
        if (patient_age is not None and patient_age <= 3 / 12) or (is_pediatric and patient_age is not None and patient_age < 1):
            if reported_temp_f is not None and reported_temp_f >= 100.4:
                return TriageAssessment(
                    urgency_level=TriageLevel.EMERGENCY,
                    red_flag_detected=True,
                    red_flag_category="NEONATAL_FEVER",
                    matched_specialty=ClinicalSpecialty.PAEDIATRICS,
                    clinical_rationale="Fever >= 100.4°F in infant under 3 months is a clinical emergency for sepsis evaluation.",
                    emergency_script_urdu=PEDIATRIC_EMERGENCY_SCRIPT
                )

        # Step 2: Check Deterministic Red-Flag Keywords
        for cat_name, pat, rationale in self.compiled_red_flags:
            if pat.search(clean_text):
                script = PEDIATRIC_EMERGENCY_SCRIPT if cat_name == "PEDIATRIC_DANGER" else EMERGENCY_SCRIPT_URDULISH
                return TriageAssessment(
                    urgency_level=TriageLevel.EMERGENCY,
                    red_flag_detected=True,
                    red_flag_category=cat_name,
                    matched_specialty=ClinicalSpecialty.CARDIOLOGY if "CARDIO" in cat_name else ClinicalSpecialty.GENERAL_MEDICINE,
                    clinical_rationale=rationale,
                    emergency_script_urdu=script
                )

        # Step 3: Urgent vs Routine Stratification
        urgency = TriageLevel.ROUTINE
        rationale = "Non-emergency routine outpatient presentation."

        # High fever, severe pain, or prolonged symptoms trigger Urgent
        if reported_temp_f and reported_temp_f >= 102.5:
            urgency = TriageLevel.URGENT
            rationale = "High fever (>= 102.5°F) warrants same-day physician evaluation."
        elif any(w in clean_text for w in ["shadeed", "severe", "3 din se bukhar", "4 din se", "bohot dard"]):
            urgency = TriageLevel.URGENT
            rationale = "Severe symptom descriptors or prolonged acute fever warrants same-day review."

        # Step 4: Specialty Mapping
        matched_spec = self._map_specialty(clean_text, patient_age, is_pediatric)

        return TriageAssessment(
            urgency_level=urgency,
            red_flag_detected=False,
            red_flag_category=None,
            matched_specialty=matched_spec,
            clinical_rationale=rationale,
            emergency_script_urdu=None
        )

    def _map_specialty(
        self,
        text: str,
        patient_age: Optional[int],
        is_pediatric: bool
    ) -> ClinicalSpecialty:
        """Deterministic specialty matcher."""
        # Pregnancy priority: Obstetric & Gynaecology conditions take precedence
        if any(w in text for w in ["pregnancy", "hamal", "periods", "mahwaari", "haiz", "pcos", "ultrasound pregnancy", "ladies doctor", "delivery", "gynaecologist", "trimester", "kick count"]):
            return ClinicalSpecialty.GYNAECOLOGY

        # Pediatric override: If under 14 years old or marked as child, route to Paediatrics
        if (patient_age is not None and patient_age < 14) or is_pediatric or any(w in text for w in ["bacha", "bachay", "bache", "bachi", "infant", "toddler", "betay"]):
            return ClinicalSpecialty.PAEDIATRICS

        # Score matching across specialties
        scores: Dict[ClinicalSpecialty, int] = {s: 0 for s in ClinicalSpecialty}
        for spec, keywords in SPECIALTY_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    scores[spec] += 1

        best_spec = max(scores, key=lambda s: scores[s])
        if scores[best_spec] > 0:
            return best_spec

        return ClinicalSpecialty.GENERAL_MEDICINE
