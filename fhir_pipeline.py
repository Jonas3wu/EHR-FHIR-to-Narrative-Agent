import json
import pandas as pd
from pathlib import Path
from collections import Counter
from google import genai
from google.genai import types

# ==========================================
# STAGE 1: FHIR Parsing & Flattening
# ==========================================

def get_code_text(resource):
    '''Extracts human-readable text from a FHIR CodeableConcept'''
    code = resource.get("code", {})
    if "text" in code:
        return code["text"]
    coding = code.get("coding", [])
    if coding:
        return coding[0].get("display") or coding[0].get("code")
    return None

def normalize_date(value):
    return str(value) if value else None

def extract_timeline_from_bundle(file_path):
    '''Parses a raw FHIR JSON bundle and flattens it into a Pandas DataFrame timeline.'''
    with open(file_path) as fh:
        data = json.load(fh)

    entries = data.get("entry", [])
    resources = [e.get("resource", {}) for e in entries]

    patient = next((r for r in resources if r.get("resourceType") == "Patient"), None)
    if not patient: return None, None
    
    patient_id = patient.get("id")
    name_dict = patient.get("name", [{}])[0]
    patient_name = f"{' '.join(name_dict.get('given', []))} {name_dict.get('family', '')}".strip()

    rows = []
    
    # Process Conditions
    for r in (res for res in resources if res.get("resourceType") == "Condition"):
        rows.append({
            "patient_id": patient_id,
            "patient_name": patient_name,
            "resource_type": "Condition",
            "date": normalize_date(r.get("onsetDateTime") or r.get("recordedDate")),
            "label": get_code_text(r)
        })
        
    # Process MedicationRequests
    for r in (res for res in resources if res.get("resourceType") == "MedicationRequest"):
        med_code = r.get("medicationCodeableConcept", {})
        label = med_code.get("text") or (med_code.get("coding", [{}])[0].get("display") if med_code.get("coding") else None)
        rows.append({
            "patient_id": patient_id,
            "patient_name": patient_name,
            "resource_type": "MedicationRequest",
            "date": normalize_date(r.get("authoredOn")),
            "label": label
        })

    # (In production, repeat extraction for Encounters, Procedures, Observations, Immunizations...)
    
    timeline_df = pd.DataFrame(rows)
    if timeline_df.empty: return None, None

    timeline_df["date_parsed"] = pd.to_datetime(timeline_df["date"], errors="coerce", utc=True)
    timeline_df = timeline_df.sort_values(["date_parsed", "resource_type", "label"]).reset_index(drop=True)
    
    # Noise Reduction: Filter out low-value repetitive observations
    timeline_clean_df = timeline_df[timeline_df["label"].notna()].copy()
    
    return timeline_df, timeline_clean_df

# ==========================================
# STAGE 2: LLM Narrative Generation
# ==========================================

FHIR_TIMELINE_SUMMARY_AGENT_SYSTEM_PROMPT = """
You are the FHIR Timeline Summary Agent.
Your job is to convert a structured patient summary into concise, professional clinical narrative prose.

Rules:
- Do not add facts not present in the input.
- Do not infer diagnoses, disease severity, treatment intent, prognosis, or outcomes.
- Preserve dates, counts, and listed conditions, medications, procedures, and immunizations accurately.
- Use neutral clinical language.
- Keep the output to 1-2 short paragraphs.
- Do not provide recommendations or decisions.
""".strip()

def run_fhir_timeline_summary_agent_gemini(summary_text, api_key, model_name="gemini-3-flash-preview"):
    '''Passes the deterministic summary to Gemini with strict safety constraints.'''
    client = genai.Client(api_key=api_key)
    user_prompt = f"Structured patient summary:\n{summary_text}"

    response = client.models.generate_content(
        model=model_name,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=FHIR_TIMELINE_SUMMARY_AGENT_SYSTEM_PROMPT,
            temperature=0.1, # Keep temperature low to prevent hallucination 
        )
    )
    return response.text
