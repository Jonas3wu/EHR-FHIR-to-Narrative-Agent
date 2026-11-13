# EHR-to-Narrative LLM Clinical Timeline Agent
## Overview & Motivation
This repository contains clinical informatics pipeline that ingests nested Electronic Health Records (EHR) in the HL7 FHIR format, flattens them into longitudinal patient event tables, and deploys a bounded Large Language Model (LLM) agent to generate zero-hallucination, clinician-friendly narrative summaries.

**The Problem: The FHIR Usability Gap**
FHIR was designed first to represent healthcare data faithfully and interoperably, not to be the easiest format for humans to read as one compact patient story. A patient’s record is not created all at once; it is built over time by many systems and people. FHIR reflects that reality by storing information as highly fragmented, linked resources. While this architecture is brilliant for system-to-system exchange and traceability, it creates a massive usability gap for clinicians who need those same data reorganized into a patient-centered, longitudinal view for efficient review. 

**The Solution**
The goal of this pipeline is to transform raw, fragmented FHIR records into structured timelines and concise summaries that are easier for clinicians and researchers to review, interpret, and use at scale. While clinical experts can synthesize these records manually for individual cases, the manual process is slow, inconsistent, and impossible to scale across larger datasets or high-throughput clinical trial workflows.

![Architecture Flowchart](fhir_pipeline_schema_aligned.png)

## Data Pipeline Stages
To see the step-by-step transformation, view the executed Jupyter Notebooks in this repository.
1. **Raw Input (FHIR Bundle):** Ingests highly nested, fragmented clinical resources (`Encounter`, `Condition`, `Observation`, etc.).
2. **Flattened Timeline:** Parses the nested JSON, filters out repetitive noise (e.g., routine BMI logs), and chronologically aligns events into a clean tabular format.
3. **Deterministic Summary (`mock_patient_summary.json`):** Aggregates the timeline into a strict, statistical text summary counting top conditions, medications, and procedures.
4. **Final LLM Narrative:** The Gemini agent rewrites the rigid statistical summary into a flowing, easy-to-read clinical narrative, strictly constrained by the system prompt to prevent hallucination.
