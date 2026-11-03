"""City Care Clinics - Medical Knowledge RAG Pipeline & Evaluation.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
RAG over Clinic FAQs, Lab Preparation Instructions, Patient Leaflets,
and Symptom-to-Specialty Mapping. Implements strict source citations and 25-question evaluation.
"""
from __future__ import annotations

import math
import os
import re
from typing import Any, Dict, List, Tuple
import chromadb
from chromadb.config import Settings

# 1. Structured Knowledge Base Documents
KNOWLEDGE_DOCUMENTS: List[Dict[str, str]] = [
    # Category 1: Clinic FAQs, Fees & Timings
    {
        "doc_id": "FAQ_FEES_TIMINGS",
        "category": "Clinic Policy",
        "title": "City Care Clinics — Official Fee Schedule & Timings",
        "section": "Fee Structure & Working Hours",
        "content": (
            "City Care Clinics operates 5 outpatient branches in Lahore and Islamabad. "
            "Working Hours: Monday through Saturday, 09:00 AM to 10:00 PM. Sunday: Closed for routine outpatient. "
            "Consultation Fees by Specialty: "
            "General Medicine: PKR 2,000 to 2,500. "
            "Paediatrics: PKR 2,200 to 3,000. "
            "Gynaecology & Obstetrics: PKR 2,500 to 3,500. "
            "Cardiology: PKR 3,000 to 4,000. "
            "Dermatology: PKR 2,200 to 2,800. "
            "ENT (Ear, Nose, Throat): PKR 2,000 to 2,800. "
            "Discounts: 20% discount applies for senior citizens (above 65 years) and active government employees on production of valid identity cards."
        )
    },
    {
        "doc_id": "FAQ_CANCELLATION",
        "category": "Clinic Policy",
        "title": "City Care Clinics — Appointment Cancellation & Rescheduling Policy",
        "section": "Cancellation Terms",
        "content": (
            "Appointments can be rescheduled or cancelled free of charge up to 2 hours before the scheduled appointment slot. "
            "If cancelled less than 2 hours before the slot, a 20% administrative fee may apply on future bookings. "
            "For emergency cancellations due to acute illness or hospitalization, no cancellation charges are levied. "
            "Patients arriving more than 20 minutes late may lose their reserved token number and be accommodated at the end of the doctor's shift."
        )
    },
    {
        "doc_id": "FAQ_BRANCH_LOCATIONS",
        "category": "Clinic Policy",
        "title": "City Care Clinics — Branch Locations & Emergency Affiliations",
        "section": "Physical Locations & Emergency Links",
        "content": (
            "1. Gulberg Branch Lahore: 14-C Main Boulevard, Gulberg III. Phone: 042-35789011. Nearby Emergency: Services Hospital (Jail Road). "
            "2. DHA Branch Lahore: Sector Y Commercial Phase 3, DHA. Phone: 042-35891234. Nearby Emergency: National Hospital DHA. "
            "3. Johar Town Branch Lahore: Plot 24 Civic Centre, Johar Town. Phone: 042-35314567. Nearby Emergency: Doctors Hospital. "
            "4. F-8 Branch Islamabad: Executive Heights, F-8 Markaz. Phone: 051-2856711. Nearby Emergency: PIMS Hospital. "
            "5. Blue Area Branch Islamabad: 72-West Jinnah Avenue. Phone: 051-2278900. Nearby Emergency: Shifa International Hospital. "
            "City Care Clinics provides outpatient care only; acute life-threatening emergencies must report directly to affiliated hospital ERs."
        )
    },

    # Category 2: Lab Test Preparation Instructions
    {
        "doc_id": "LAB_PREP_LIPID_SUGAR",
        "category": "Lab Preparation",
        "title": "Patient Instructions — Fasting Blood Sugar & Lipid Profile",
        "section": "Fasting Requirements",
        "content": (
            "Fasting Blood Sugar (FBS) requires a strict fast of 8 to 10 hours before the morning blood draw. "
            "Fasting Lipid Profile (Cholesterol, Triglycerides, HDL, LDL) requires a strict fast of 10 to 12 hours. "
            "During the fasting window: You may drink plain water only. Do not drink tea, coffee, milk, juice, or chew gum. "
            "Routine morning blood pressure medications should be taken with small sips of water unless instructed otherwise. "
            "Do not take insulin or oral diabetes tablets on the morning of fasting blood draw until after blood is collected."
        )
    },
    {
        "doc_id": "LAB_PREP_HBA1C",
        "category": "Lab Preparation",
        "title": "Patient Instructions — Glycated Hemoglobin (HbA1c) Testing",
        "section": "HbA1c Preparation",
        "content": (
            "HbA1c test measures the 3-month average blood glucose control. "
            "Fasting is NOT required for an HbA1c test. You can eat, drink, and take your regular medications normally prior to the test. "
            "The test can be conducted at any time of day during clinic lab hours (08:00 AM to 08:00 PM). "
            "Reference Ranges: Normal is below 5.7%. Pre-diabetes is 5.7% to 6.4%. Diabetes is 6.5% or higher."
        )
    },
    {
        "doc_id": "LAB_PREP_ULTRASOUND",
        "category": "Lab Preparation",
        "title": "Patient Instructions — Pelvic & Abdominal Ultrasound Preparation",
        "section": "Ultrasound Preparation Protocols",
        "content": (
            "Abdominal Ultrasound (Liver, Gallbladder, Pancreas, Spleen): Requires 6 to 8 hours of fasting to minimize bowel gas and ensure gallbladder distension. "
            "Pelvic / Obstetric / Urinary Bladder Ultrasound: Requires a full urinary bladder. "
            "Drink 4 to 6 glasses of plain water 1 hour before the scheduled ultrasound scan and do not urinate until the scan is complete. "
            "For transvaginal ultrasound (TVS), an empty bladder is preferred."
        )
    },
    {
        "doc_id": "LAB_PREP_URINE_CULTURE",
        "category": "Lab Preparation",
        "title": "Patient Instructions — Clean Catch Midstream Urine Sample",
        "section": "Urine Routine & Culture Collection",
        "content": (
            "Clean Catch Midstream Urine Collection: Wash hands thoroughly before opening the sterile container. "
            "Clean the genital area with clean water. Discard the first 10-20 mL of urine into the toilet bowl. "
            "Collect the middle stream of urine directly into the sterile container without touching the inner rim or cap. "
            "Deliver the sample to the clinic laboratory within 1 hour of collection. Do not start antibiotics before collecting a urine culture sample."
        )
    },

    # Category 3: Patient-Education Leaflets (Bilingual Context)
    {
        "doc_id": "LEAFLET_HYPERTENSION",
        "category": "Patient Education",
        "title": "Clinical Education — Hypertension (High Blood Pressure) Care",
        "section": "High Blood Pressure Guidelines",
        "content": (
            "High Blood Pressure (Hypertension) is defined as systolic BP 130 mmHg or higher, or diastolic BP 80 mmHg or higher on repeated measurements. "
            "UrduLish Guidance: High BP aksar 'khamosh qatil' (silent killer) hota hai jis ki aam tor par koi alamaat nahi hotiin. "
            "Dietary Advice: Reduce dietary sodium (table salt) to less than 1 teaspoon per day. Avoid pickles, papad, processed meats, and salty snacks. "
            "Exercise: 30 minutes of brisk walking 5 days a week. "
            "Danger Signs: If blood pressure exceeds 180/120 mmHg, or is accompanied by chest pain, severe headache, or blurred vision, seek immediate emergency care."
        )
    },
    {
        "doc_id": "LEAFLET_DIABETES",
        "category": "Patient Education",
        "title": "Clinical Education — Type 2 Diabetes Mellitus Management",
        "section": "Diabetes Lifestyle & Foot Care",
        "content": (
            "Type 2 Diabetes requires lifelong management of blood sugar through diet, exercise, and prescribed medications. "
            "Diet: Limit refined carbohydrates (mithai, white rice, naan, cold drinks, juices). Choose high-fiber whole wheat roti and green vegetables. "
            "Foot Care (Paaon ki hifazat): Inspect your feet daily for cuts, blisters, or redness. Never walk barefoot, even indoors. Wash feet daily with lukewarm water and dry thoroughly between toes. "
            "Hypoglycemia (Low Sugar Alert): If blood sugar drops below 70 mg/dL (trembling, cold sweat, hunger, dizziness), immediately consume 15g fast-acting sugar (half glass juice or 3 sugar candies)."
        )
    },
    {
        "doc_id": "LEAFLET_DENGUE",
        "category": "Patient Education",
        "title": "Clinical Education — Dengue Fever Home Care & Warning Signs in Pakistan",
        "section": "Dengue Management & Red Flags",
        "content": (
            "Dengue fever is caused by mosquito bites (Aedes aegypti) common in Lahore and Islamabad during post-monsoon months. "
            "Home Care: Strict bed rest and abundant oral hydration (ORS, coconut water, soup, apple juice). "
            "Medication Safety: Use Paracetamol ONLY for fever/body aches. NEVER TAKE Aspirin, Disprin, Brufen (Ibuprofen), or Diclofenac as they severely increase internal bleeding risk. "
            "Critical Warning Signs: Persistent vomiting, severe abdominal pain, bleeding gums/nose, extreme lethargy, or rapid drop in platelets warrant immediate hospital admission."
        )
    },
    {
        "doc_id": "LEAFLET_INFANT_FEVER",
        "category": "Patient Education",
        "title": "Clinical Education — Infant & Child Fever Management",
        "section": "Pediatric Fever Protocol",
        "content": (
            "Fever in children (bachon ka bukhar): Fever is the body's natural response to infections. "
            "Chotay bachon mein bukhar (Infants under 3 months / 3 mahine se chotay bachay): Any rectal/axillary fever >= 38.0°C (100.4°F) is a medical emergency requiring hospital evaluation for neonatal sepsis. "
            "Children over 3 months: Keep the child comfortably dressed in light cotton clothes. Keep the room well-ventilated. Offer frequent fluids or breast milk. "
            "Sponge bath with lukewarm water (never cold water or ice). "
            "Bachon ko bukhar mein Aspirin hargiz na dein: Never give Aspirin to children due to fatal risk of Reye's Syndrome (Reye's syndrome ka khatra). "
            "Consult a paediatrician for exact paracetamol dosing by weight."
        )
    },

    # Category 4: Symptom-to-Specialty Mapping
    {
        "doc_id": "MAP_SPECIALTY_GUIDE",
        "category": "Specialty Directory",
        "title": "Clinical Routing Guide — Symptom-to-Specialty Mapping Table",
        "section": "Specialty Matching Rules",
        "content": (
            "Clinical routing rules for City Care Clinics (Kis doctor ya specialty ko dikhana chahiye): "
            "1. General Medicine (Internal Medicine): Adult fever, cough, flu, diabetes, hypertension, generalized weakness, unexplained weight loss, digestive issues. "
            "2. Paediatrics: Children under 14 years old with fever, cough, vomiting, failure to thrive, growth concerns, vaccination schedules. "
            "3. Gynaecology & Obstetrics: Pregnancy care, irregular menstrual cycles, PCOS, pelvic pain, prenatal checkups, post-partum recovery. "
            "4. Cardiology: Chest tightness on exertion, palpitations, high blood pressure refractory to therapy, leg swelling, history of stents or bypass. "
            "5. Dermatology (Jild ke amraz): Skin rashes, acne, hair loss, eczema, psoriasis, fungal nail infections, unexplained moles or itching (jild par rash, daanay, kharish). "
            "6. ENT (Otolaryngology): Sore throat, tonsillitis, ear pain, ear discharge, hearing loss, nasal blockage, sinus congestion, dizziness/vertigo (kaan mein dard, gala kharab)."
        )
    }
]


class MedicalKnowledgeRAG:
    """Production RAG Engine for City Care Clinics Knowledge Base."""

    def __init__(self, persist_dir: str = None):
        if not persist_dir:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            persist_dir = os.path.join(base_dir, "chroma_db")

        os.makedirs(persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_dir, settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(
            name="clinic_medical_kb",
            metadata={"description": "City Care Clinics Verified Medical Knowledge"}
        )
        self._populate_kb()

    def _populate_kb(self):
        """Indexes knowledge base documents into ChromaDB."""
        ids = [doc["doc_id"] for doc in KNOWLEDGE_DOCUMENTS]
        documents = [f"{doc['title']}\nSection: {doc['section']}\nCategory: {doc['category']}\n{doc['content']}" for doc in KNOWLEDGE_DOCUMENTS]
        metadatas = [
            {"doc_id": doc["doc_id"], "title": doc["title"], "section": doc["section"], "category": doc["category"]}
            for doc in KNOWLEDGE_DOCUMENTS
        ]

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieves top-k relevant knowledge chunks with hybrid dense + lexical ranking."""
        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k + 2, self.collection.count())
        )

        retrieved_chunks = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
            dists = results["distances"][0] if "distances" in results and results["distances"] else [0.0] * len(docs)

            for doc_text, meta, dist in zip(docs, metas, dists):
                confidence = round(1.0 / (1.0 + float(dist)), 3) if dist is not None else 0.85
                retrieved_chunks.append({
                    "doc_id": meta.get("doc_id", "DOC_UNKNOWN"),
                    "title": meta.get("title", "Clinical Guide"),
                    "section": meta.get("section", "General"),
                    "category": meta.get("category", "General"),
                    "content": doc_text,
                    "confidence": confidence
                })

        # Hybrid reranking: combine dense similarity with lexical token overlap
        query_words = set(re.findall(r'[a-zA-Z0-9]+', query.lower()))
        for item in retrieved_chunks:
            doc_words = set(re.findall(r'[a-zA-Z0-9]+', item['content'].lower()))
            overlap = len(query_words.intersection(doc_words))
            item['combined_score'] = item['confidence'] + (overlap * 0.12)

        retrieved_chunks.sort(key=lambda x: x['combined_score'], reverse=True)
        return retrieved_chunks[:top_k]

    def answer_question(self, query: str) -> Dict[str, Any]:
        """Synthesizes grounded response with mandatory source citations."""
        chunks = self.retrieve(query, top_k=2)
        if not chunks or chunks[0]["confidence"] < 0.30:
            return {
                "query": query,
                "answer": (
                    "Mohtaram patient, is sawal ke mutalliq hamare clinic database mein certified maloomat dastiyab nahi hain. "
                    "Baraye meharbani hamare clinic helpline 042-35789011 par rabta karein ya doctor se consultation schedule karein."
                ),
                "citations": [],
                "is_grounded": False
            }

        top_chunk = chunks[0]
        citations = [
            {
                "doc_id": c["doc_id"],
                "source": c["title"],
                "section": c["section"],
                "confidence": c["confidence"]
            }
            for c in chunks
        ]

        # Grounded factual response synthesis
        answer_text = (
            f"Bamuqabla City Care Clinics Verified Guidelines ({top_chunk['title']} — {top_chunk['section']}):\n"
            f"{top_chunk['content'].split(chr(10))[-1]}\n\n"
            f"[Source Citation: {top_chunk['title']} | Section: {top_chunk['section']} | Ref: {top_chunk['doc_id']}]"
        )

        return {
            "query": query,
            "answer": answer_text,
            "citations": citations,
            "is_grounded": True
        }


# 2. 25 Ground Truth Evaluation Benchmark Questions
EVALUATION_QUESTIONS: List[Dict[str, Any]] = [
    {"q": "Lipid profile test se pehle kitne ghante bhooka (fasting) rehna chahiye?", "expected_doc": "LAB_PREP_LIPID_SUGAR", "must_contain": ["10 to 12 hours", "fast"]},
    {"q": "Fasting blood sugar test ke liye kitni fasting required hai?", "expected_doc": "LAB_PREP_LIPID_SUGAR", "must_contain": ["8 to 10 hours"]},
    {"q": "Kya HbA1c test ke liye fasting zaroori hai?", "expected_doc": "LAB_PREP_HBA1C", "must_contain": ["fasting is not required", "not required"]},
    {"q": "Normal HbA1c reference range kitni hoti hai?", "expected_doc": "LAB_PREP_HBA1C", "must_contain": ["5.7%"]},
    {"q": "Pelvic ultrasound se pehle kitna paani peena chahiye?", "expected_doc": "LAB_PREP_ULTRASOUND", "must_contain": ["4 to 6 glasses", "full urinary bladder"]},
    {"q": "Abdominal ultrasound ke liye kitni fasting chahiye?", "expected_doc": "LAB_PREP_ULTRASOUND", "must_contain": ["6 to 8 hours"]},
    {"q": "Urine culture sample kaise collect karna chahiye?", "expected_doc": "LAB_PREP_URINE_CULTURE", "must_contain": ["clean catch midstream", "midstream"]},
    {"q": "General Medicine doctor ki consultation fees kitni hai?", "expected_doc": "FAQ_FEES_TIMINGS", "must_contain": ["2,000", "2,500"]},
    {"q": "Cardiology specialist ki consultation fees kya hai?", "expected_doc": "FAQ_FEES_TIMINGS", "must_contain": ["3,000 to 4,000"]},
    {"q": "Kya senior citizens ko consultation fee par discount milta hai?", "expected_doc": "FAQ_FEES_TIMINGS", "must_contain": ["20% discount", "senior citizens"]},
    {"q": "Clinic ke working hours aur timings kya hain?", "expected_doc": "FAQ_FEES_TIMINGS", "must_contain": ["09:00 AM to 10:00 PM", "Monday through Saturday"]},
    {"q": "Appointment cancellation policy kya hai, kitne ghante pehle cancel kar sakte hain?", "expected_doc": "FAQ_CANCELLATION", "must_contain": ["2 hours"]},
    {"q": "Lahore Gulberg branch ka address aur emergency hospital kaunsa hai?", "expected_doc": "FAQ_BRANCH_LOCATIONS", "must_contain": ["Gulberg III", "Services Hospital"]},
    {"q": "Islamabad Blue Area branch ka nearby emergency hospital kaunsa hai?", "expected_doc": "FAQ_BRANCH_LOCATIONS", "must_contain": ["Shifa International Hospital"]},
    {"q": "Islamabad F-8 branch ka emergency hospital kaunsa hai?", "expected_doc": "FAQ_BRANCH_LOCATIONS", "must_contain": ["PIMS Hospital"]},
    {"q": "Dengue fever mein kaunsi dard ki dawai bilkul nahi leni chahiye?", "expected_doc": "LEAFLET_DENGUE", "must_contain": ["Aspirin", "Brufen", "Disprin"]},
    {"q": "Dengue mein bukhar ke liye sirf kaunsi dawai safe hai?", "expected_doc": "LEAFLET_DENGUE", "must_contain": ["Paracetamol"]},
    {"q": "High blood pressure (Hypertension) ki definition kya hai?", "expected_doc": "LEAFLET_HYPERTENSION", "must_contain": ["130", "80"]},
    {"q": "High BP ke mareez ko rozana kitna namak lena chahiye?", "expected_doc": "LEAFLET_HYPERTENSION", "must_contain": ["1 teaspoon", "salt"]},
    {"q": "Type 2 diabetes ke mareez ko paaon ki hifazat (foot care) kaise karni chahiye?", "expected_doc": "LEAFLET_DIABETES", "must_contain": ["never walk barefoot", "inspect"]},
    {"q": "Low blood sugar (hypoglycemia) ki soorat mein foran kya lena chahiye?", "expected_doc": "LEAFLET_DIABETES", "must_contain": ["15g fast-acting sugar", "juice"]},
    {"q": "3 mahine se chotay bachay ko bukhar ho to kya karna chahiye?", "expected_doc": "LEAFLET_INFANT_FEVER", "must_contain": ["medical emergency", "neonatal sepsis"]},
    {"q": "Bachon ko bukhar mein Aspirin kyun nahi deni chahiye?", "expected_doc": "LEAFLET_INFANT_FEVER", "must_contain": ["Reye's Syndrome"]},
    {"q": "Gala kharab aur kaan ke dard ke liye kis doctor ko dikhana chahiye?", "expected_doc": "MAP_SPECIALTY_GUIDE", "must_contain": ["ENT"]},
    {"q": "Jild par rash aur kharish ho to kis specialty mein jana chahiye?", "expected_doc": "MAP_SPECIALTY_GUIDE", "must_contain": ["Dermatology"]}
]


def run_rag_evaluation(rag: MedicalKnowledgeRAG = None) -> Dict[str, Any]:
    """Evaluates RAG pipeline across 25 ground-truth benchmark questions."""
    if rag is None:
        rag = MedicalKnowledgeRAG()

    total_questions = len(EVALUATION_QUESTIONS)
    grounded_count = 0
    hallucination_count = 0
    top1_correct_source_count = 0
    detailed_results = []

    for item in EVALUATION_QUESTIONS:
        query = item["q"]
        expected_doc = item["expected_doc"]
        must_contains = item["must_contain"]

        res = rag.answer_question(query)
        retrieved_doc_ids = [c["doc_id"] for c in res["citations"]]
        top_doc_id = retrieved_doc_ids[0] if retrieved_doc_ids else None

        # 1. Source Precision
        source_matched = (top_doc_id == expected_doc)
        if source_matched:
            top1_correct_source_count += 1

        # 2. Grounding check
        answer_text_lower = res["answer"].lower()
        has_supported_content = any(term.lower() in answer_text_lower for term in must_contains)

        if has_supported_content and res["is_grounded"]:
            grounded_count += 1
            is_hallucination = False
        else:
            is_hallucination = True
            hallucination_count += 1

        detailed_results.append({
            "question": query,
            "expected_doc": expected_doc,
            "retrieved_doc": top_doc_id,
            "source_matched": source_matched,
            "grounded": has_supported_content,
            "hallucination": is_hallucination,
            "citations": res["citations"]
        })

    grounding_rate = round((grounded_count / total_questions) * 100, 2)
    hallucination_rate = round((hallucination_count / total_questions) * 100, 2)
    retrieval_accuracy = round((top1_correct_source_count / total_questions) * 100, 2)

    summary = {
        "total_questions": total_questions,
        "grounding_rate_percent": grounding_rate,
        "hallucination_rate_percent": hallucination_rate,
        "top1_retrieval_accuracy_percent": retrieval_accuracy,
        "grounded_count": grounded_count,
        "hallucination_count": hallucination_count,
        "detailed_results": detailed_results
    }

    return summary


if __name__ == "__main__":
    rag = MedicalKnowledgeRAG()
    eval_res = run_rag_evaluation(rag)
    print("=" * 70)
    print("MEDICAL KNOWLEDGE RAG EVALUATION BENCHMARK (25 QUESTIONS)")
    print("=" * 70)
    print(f"Total Questions Evaluated:  {eval_res['total_questions']}")
    print(f"Grounding Rate:             {eval_res['grounding_rate_percent']}%")
    print(f"Hallucination Rate:         {eval_res['hallucination_rate_percent']}%")
    print(f"Top-1 Retrieval Precision:  {eval_res['top1_retrieval_accuracy_percent']}%")
    print("=" * 70)
