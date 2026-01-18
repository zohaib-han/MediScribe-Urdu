import os
import base64
import re
from typing import Dict, Any
from gtts import gTTS


class VisionAgent:
    def __init__(self, api_key_env: str = "GEMINI_API_KEY"):
        self.api_key = os.getenv(api_key_env)

    def _read_image_base64(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode("utf-8")

    def build_gemini_image_prompt(self) -> Dict[str, Any]:
        return {
            "prompt": (
                "You are a high-accuracy handwriting recognition assistant for medical prescriptions.\n"
                "Task: Extract all text from the provided prescription image.\n"
                "Requirements:\n"
                " - Return raw text exactly as read (do not translate or paraphrase) under 'raw_text'.\n"
                " - If uncertain about a word, add '[?]' after it.\n"
                " - Identify likely medication names, dosages, and scheduling abbreviations and tag them as 'medications'.\n"
                " - Provide confidence estimates (High/Med/Low) for each medication line.\n"
                "Output format: JSON with keys: raw_text (string), medications (list of {name, dose, schedule, confidence}).\n"
            )
        }

    def extract_text_from_image(self, image_path: str) -> Dict[str, Any]:
        image_b64 = self._read_image_base64(image_path)
        prompt_meta = self.build_gemini_image_prompt()

        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not set. Set environment variable before calling VisionAgent.")

        # TODO: Replace with actual Gemini API call
        simulated_response = {
            "raw_text": "Tabzole 500mg 1 tablet OD\nParacetamol 500 mg 1 tab SOS\nAmoxicillin 250mg 1-0-1 for 5 days",
            "medications": [
                {"name": "Tabzole", "dose": "500mg", "schedule": "1 tablet OD", "confidence": "Med"},
                {"name": "Paracetamol", "dose": "500 mg", "schedule": "1 tab SOS", "confidence": "High"},
                {"name": "Amoxicillin", "dose": "250mg", "schedule": "1-0-1", "confidence": "Med"}
            ]
        }
        return simulated_response


class PharmacistAgent:
    DRUG_ALIASES = {
        "Tabzole": "Tabzole (Albendazole)",
        "Amoxil": "Amoxicillin",
        "Amoxycillin": "Amoxicillin",
        "Paracetamol": "Paracetamol"
    }

    ABBREVIATION_MAP = {
        "OD": "once daily",
        "BD": "twice daily",
        "BID": "twice daily",
        "TDS": "three times daily",
        "HS": "at bedtime",
        "SOS": "as needed",
        "PRN": "as needed"
    }

    def _normalize_drug_name(self, name: str) -> str:
        name_clean = re.sub(r"[^A-Za-z0-9\s-]", "", name).strip()
        for alias, standard in self.DRUG_ALIASES.items():
            if name_clean.lower().startswith(alias.lower()):
                return standard
        return name_clean

    def _expand_abbreviations(self, schedule: str) -> str:
        parts = schedule.split()
        expanded = []
        for p in parts:
            token = p.strip().upper().strip(".,")
            expanded.append(self.ABBREVIATION_MAP.get(token, p))
        return " ".join(expanded)

    def correct_medications(self, vision_output: dict) -> dict:
        medications = vision_output.get("medications", [])
        corrected = []

        for med in medications:
            name = self._normalize_drug_name(med.get("name", "").strip())
            dose = med.get("dose", "").strip()
            schedule = self._expand_abbreviations(med.get("schedule", "").strip())

            corrected.append({
                "name": name,
                "dose": dose,
                "schedule": schedule,
                "confidence": med.get("confidence", "Low")
            })

        vision_output["medications_clean"] = corrected
        return vision_output


class LinguistAgent:
    def __init__(self, api_key_env: str = "GEMINI_API_KEY"):
        self.api_key = os.getenv(api_key_env)

    def build_urdu_prompt(self, medications_clean: list) -> str:
        meds_text = "\n".join([
            f"- {m['name']} | {m['dose']} | {m['schedule']}"
            for m in medications_clean
        ])

        instruction = (
            "You are an assistant that converts medical prescriptions into very simple, "
            "conversational Urdu suitable for low-literacy patients.\n"
            "Constraints:\n"
            " - Use short sentences and everyday Urdu (not formal literary Urdu).\n"
            " - For each medicine, tell the name, how much to take, when to take it, and "
            "a one-line purpose in Urdu (if common).\n"
            " - If the schedule contains 'as needed' (SOS/PRN), explain in Urdu when to take it.\n"
            " - Avoid technical jargon; use examples like 'صبح، دوپہر، رات' and numerals for doses.\n"
            "Output: Return only the Urdu text block (no JSON).\n\n"
            "Medications:\n"
            f"{meds_text}\n\n"
            "Produce the final spoken Urdu instructions now."
        )
        return instruction

    def generate_urdu_text(self, medications_clean: list) -> str:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not set. Set environment variable before calling LinguistAgent.")

        # TODO: Replace with actual Gemini API call
        simulated_urdu = (
            "آپ کو روزانہ صبح ایک گولی Tabzole (Albendazole) لینا ہے۔\n"
            "اگر بخار یا درد ہو تو Paracetamol 500 mg ایک گولی ضرورت کے وقت لے لیں۔\n"
            "Amoxicillin 250 mg صبح اور رات ایک ایک گولی، پانچ دن تک لیں۔\n"
        )
        return simulated_urdu


class TTS:
    def synthesize_urdu(self, urdu_text: str, output_path: str = "output.mp3") -> str:
        try:
            tts = gTTS(text=urdu_text, lang="ur")
            tts.save(output_path)
            return output_path
        except Exception as e:
            raise RuntimeError(f"TTS (gTTS) failed: {str(e)}")


class ManagerAgent:
    def __init__(self):
        self.vision = VisionAgent()
        self.pharmacist = PharmacistAgent()
        self.linguist = LinguistAgent()
        self.tts = TTS()

    def process_prescription(self, image_path: str, synthesize_audio: bool = False) -> dict:
        vision_out = self.vision.extract_text_from_image(image_path)
        cleaned = self.pharmacist.correct_medications(vision_out)
        urdu_text = self.linguist.generate_urdu_text(
            cleaned.get("medications_clean", [])
        )

        result = {
            "raw_text": vision_out.get("raw_text"),
            "medications_clean": cleaned.get("medications_clean"),
            "urdu_text": urdu_text
        }

        if synthesize_audio:
            audio_path = self.tts.synthesize_urdu(urdu_text, output_path="prescription_urdu.mp3")
            result["audio_path"] = audio_path

        return result
