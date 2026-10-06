"""
CivicPulse AI - AI Vision Inspection Engine
Integrates Google Gemini 2.5 Flash for multimodal infrastructure issue analysis.
Features:
- Structured JSON output (issue_type, severity 1-5, confidence, description, safety risk)
- Detection of invalid/irrelevant images (selfies, pets, food, indoor items)
- Resilient Fallback Demo Mode if API key is not configured or rate-limited.
"""

import os
import json
import re
from typing import Dict, Any, Optional
from PIL import Image

try:
    import streamlit as st
except ImportError:
    st = None


def get_gemini_api_key(manual_key: Optional[str] = None) -> Optional[str]:
    """
    Retrieves Gemini API Key from:
    1. Direct manual input in UI (if provided)
    2. Streamlit secrets (st.secrets["GEMINI_API_KEY"])
    3. Environment variable (GEMINI_API_KEY)
    """
    if manual_key and manual_key.strip():
        return manual_key.strip()

    if st:
        try:
            if "GEMINI_API_KEY" in st.secrets:
                return st.secrets["GEMINI_API_KEY"].strip()
        except Exception:
            pass

    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    return None


SYSTEM_PROMPT = """
You are an expert Civil Infrastructure Safety Inspector and Computer Vision AI for municipal corporations.
Analyze the provided image to detect, classify, and evaluate public infrastructure defects.

Valid issue types:
- "pothole" (cavity, depression, or crater on road/asphalt)
- "damaged road" (cracks, uneven surface, erosion, caved-in road)
- "broken streetlight" (damaged lamp post, non-functional light, hanging wires)
- "overflowing drain" (clogged storm drain, open manhole, sewage leak, waterlogging)
- "other" (other municipal infrastructure issue like broken railing, fallen sign, dangerous debris)
- "none" (if the image DOES NOT show public infrastructure, e.g. a selfie, pet, indoor room, food, vehicle interior, document, or unrelated scene)

You MUST respond strictly with a valid JSON object matching this schema:
{
  "is_valid_infrastructure_issue": boolean,
  "issue_type": "pothole" | "damaged road" | "broken streetlight" | "overflowing drain" | "other" | "none",
  "severity": integer between 1 and 5 (1=minor cosmetic wear, 3=moderate hazard requiring scheduled repair, 5=extreme critical emergency posing immediate danger to life/limb),
  "confidence": float between 0.0 and 1.0,
  "short_description": "concise 1-2 sentence description of the defect observed",
  "safety_risk_reason": "specific danger posed to citizens, pedestrians, or vehicles (e.g. fatal skid risk for two-wheelers, pedestrian fall into open drain, road collapse)",
  "rejection_reason": "only explain if is_valid_infrastructure_issue is false, otherwise null"
}
Output raw JSON only. Do not wrap in markdown quotes or preamble.
"""


def _clean_json_response(raw_text: str) -> Dict[str, Any]:
    """Clean markdown code fences and parse JSON safely."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Search for first { and last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]

    return json.loads(text)


def analyze_infrastructure_image(
    image: Image.Image,
    manual_api_key: Optional[str] = None,
    image_filename: str = ""
) -> Dict[str, Any]:
    """
    Sends the image to Google Gemini Vision API.
    Returns structured analysis dictionary.
    Falls back gracefully to Demo Simulation Mode if no key or API error.
    """
    api_key = get_gemini_api_key(manual_api_key)

    if not api_key:
        return _fallback_simulation(image, image_filename, reason="No Gemini API Key provided")

    # Try Google GenAI SDK (google-genai or google-generativeai)
    # Attempt 1: google-genai (latest official SDK)
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[SYSTEM_PROMPT, image],
        )

        if response and response.text:
            parsed = _clean_json_response(response.text)
            parsed["mode"] = "live_gemini_2_5"
            return _normalize_analysis(parsed)

    except Exception as e1:
        # Attempt 2: google.generativeai (classic SDK)
        try:
            import google.generativeai as genai_classic
            genai_classic.configure(api_key=api_key)

            # Try 2.5-flash or 1.5-flash
            for model_name in ["gemini-2.5-flash", "gemini-1.5-flash"]:
                try:
                    model = genai_classic.GenerativeModel(model_name)
                    response = model.generate_content([SYSTEM_PROMPT, image])
                    if response and response.text:
                        parsed = _clean_json_response(response.text)
                        parsed["mode"] = f"live_{model_name}"
                        return _normalize_analysis(parsed)
                except Exception:
                    continue

        except Exception as e2:
            pass

        # If both fail (network error, invalid key, or quota exhausted), use fallback
        return _fallback_simulation(
            image,
            image_filename,
            reason=f"Gemini API call encountered an issue ({type(e1).__name__}). Using offline simulation."
        )

    return _fallback_simulation(image, image_filename, reason="Unable to get response from Gemini")


def _normalize_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize fields to ensure consistent data types."""
    issue_type = str(data.get("issue_type", "other")).lower().strip()
    valid_types = ["pothole", "damaged road", "broken streetlight", "overflowing drain", "other", "none"]
    if issue_type not in valid_types:
        issue_type = "other"

    try:
        severity = int(data.get("severity", 3))
        severity = max(1, min(5, severity))
    except Exception:
        severity = 3

    try:
        confidence = float(data.get("confidence", 0.90))
        confidence = max(0.0, min(1.0, confidence))
    except Exception:
        confidence = 0.90

    is_valid = bool(data.get("is_valid_infrastructure_issue", issue_type != "none"))
    if issue_type == "none":
        is_valid = False

    return {
        "is_valid_infrastructure_issue": is_valid,
        "issue_type": issue_type,
        "severity": severity,
        "confidence": round(confidence, 2),
        "short_description": str(data.get("short_description", "Infrastructure defect detected.")),
        "safety_risk_reason": str(data.get("safety_risk_reason", "Potential safety hazard for passing citizens and vehicles.")),
        "rejection_reason": data.get("rejection_reason") if not is_valid else None,
        "mode": data.get("mode", "live_gemini")
    }


def _fallback_simulation(
    image: Image.Image,
    filename: str = "",
    reason: str = ""
) -> Dict[str, Any]:
    """
    Intelligent Demo Mode for hackathon presentations:
    Ensures the demo ALWAYS works seamlessly even without an internet connection or API quota!
    """
    fname = filename.lower()

    if "pothole" in fname:
        issue_type = "pothole"
        severity = 4
        confidence = 0.96
        desc = "Deep crater/pothole (~18 inches wide) on asphalt carriageway with exposed aggregates."
        risk = "Critical risk of two-wheeler handle loss and severe accidents, especially during nighttime or rain."
    elif "drain" in fname or "sewage" in fname or "water" in fname:
        issue_type = "overflowing drain"
        severity = 5
        confidence = 0.94
        desc = "Overflowing roadside storm drainage with stagnant wastewater submerging sidewalk."
        risk = "Severe biological contamination, dengue vector breeding risk, and structural undermining of adjacent road."
    elif "light" in fname or "pole" in fname:
        issue_type = "broken streetlight"
        severity = 3
        confidence = 0.91
        desc = "Non-functional sodium-vapor streetlight fixture with exposed electrical box wiring."
        risk = "Reduced night visibility leading to pedestrian tripping and elevated nighttime security hazards."
    elif "road" in fname or "crack" in fname:
        issue_type = "damaged road"
        severity = 3
        confidence = 0.88
        desc = "Longitudinal alligator cracking and surface spalling across both vehicular lanes."
        risk = "Accelerated road deterioration and vehicular tire wear; potential hazard under sudden braking."
    elif "cat" in fname or "selfie" in fname or "pet" in fname or "meme" in fname:
        return {
            "is_valid_infrastructure_issue": False,
            "issue_type": "none",
            "severity": 1,
            "confidence": 0.98,
            "short_description": "Non-infrastructure image detected (pet/domestic subject).",
            "safety_risk_reason": "No public municipal safety risk found.",
            "rejection_reason": "Image appears to be a domestic pet or selfie, not public municipal infrastructure. Report rejected.",
            "mode": "demo_simulation",
            "demo_note": reason
        }
    else:
        # Default realistic infrastructure detection for uploaded samples
        issue_type = "pothole"
        severity = 4
        confidence = 0.92
        desc = "Prominent road depression and asphalt deterioration identified on primary lane."
        risk = "High hazard for cyclists, two-wheelers, and low-clearance vehicles."

    return {
        "is_valid_infrastructure_issue": True,
        "issue_type": issue_type,
        "severity": severity,
        "confidence": confidence,
        "short_description": desc,
        "safety_risk_reason": risk,
        "rejection_reason": None,
        "mode": "demo_simulation",
        "demo_note": reason
    }
