"""
MediScribe Agents Pipeline - Gemini + ElevenLabs Integration
A multi-agent system for processing medical prescriptions with OCR, correction,
translation to Urdu, and high-quality text-to-speech generation.

Author: MediScribe Team
Version: 2.0 (ElevenLabs Integration)
Date: December 8, 2025
"""

import os
import re
import json
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from PIL import Image
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# Configuration
# ============================================================================


class Config:
    """Central configuration for the MediScribe pipeline"""

    # API Configuration
    # Note: It is best practice to use Environment Variables rather than hardcoding keys.
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    GEMINI_MODEL = 'gemini-flash-latest'  # Use gemini-1.5-pro for better accuracy

    # ElevenLabs TTS Configuration
    ELEVENLABS_MODEL = "eleven_multilingual_v2"  # Supports Urdu
    # Default voice - can be changed to any Urdu voice
    ELEVENLABS_VOICE = "JBFqnCBsd6RMkjVDRZzb"

    # Voice Settings for ElevenLabs
    VOICE_SETTINGS = {
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0.0,
        "use_speaker_boost": True
    }

    # Drug Aliases Mapping
    DRUG_ALIASES = {
        "Tabzole": "Tabzole (Albendazole)",
        "Amoxil": "Amoxicillin",
        "Amoxycillin": "Amoxicillin",
        "Paracetamol": "Paracetamol",
        "Augmentin": "Amoxicillin-Clavulanate",
        "Brufen": "Ibuprofen",
        "Disprin": "Aspirin",
        "Flagyl": "Metronidazole"
    }

    # Medical Abbreviations
    ABBREVIATION_MAP = {
        "OD": "once daily",
        "BD": "twice daily",
        "BID": "twice daily",
        "TDS": "three times daily",
        "TID": "three times daily",
        "QID": "four times daily",
        "HS": "at bedtime",
        "SOS": "as needed",
        "PRN": "as needed",
        "AC": "before meals",
        "PC": "after meals",
        "STAT": "immediately",
        "QH": "every hour",
        "Q4H": "every 4 hours",
        "Q6H": "every 6 hours",
        "Q8H": "every 8 hours"
    }

    # Default file paths
    DEFAULT_AUDIO_OUTPUT = r"C:\Users\abdre\Desktop\my_prescription.mp3"
    TEST_AUDIO_OUTPUT = "elevenlabs_urdu_test.mp3"

    # Supported image formats
    SUPPORTED_IMAGE_FORMATS = [
        '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff','.webp']

# ============================================================================
# Agent Classes
# ============================================================================


class VisionAgent:
    """
    Extracts text from prescription images using multimodal LLM (Gemini).

    Handles handwritten text recognition (HTR) for medical prescriptions,
    identifying medication names, dosages, and schedules.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: str = Config.GEMINI_MODEL):
        """
        Initialize Vision Agent.

        Args:
            api_key: Gemini API key. If None, reads from environment.
            model_name: Gemini model to use
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not set. Provide via parameter or environment variable."
            )

        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)

    def _build_vision_prompt(self) -> str:
        """
        Construct prompt for the vision model.

        Returns:
            Detailed prompt string for accurate HTR
        """
        return """You are a high-accuracy handwriting recognition assistant for medical prescriptions.

Task: Extract all text from the provided prescription image.

Requirements:
- Return raw text exactly as read (do not translate or paraphrase) under 'raw_text'.
- If uncertain about a word, add '[?]' after it.
- Identify likely medication names, dosages, and scheduling abbreviations and tag them as 'medications'.
- Provide confidence estimates (High/Med/Low) for each medication line.
- Extract patient information if visible (name, age, date).
- Include any special instructions or warnings.

Output format: JSON with keys:
{
  "raw_text": "string with all extracted text",
  "medications": [
    {"name": "medication name", "dose": "dosage",
        "schedule": "timing", "confidence": "High/Med/Low"}
  ],
  "patient_info": {
    "name": "patient name if visible",
    "age": "age if visible",
    "date": "prescription date if visible"
  },
  "special_instructions": "any special notes or warnings"
}

Return ONLY valid JSON, no additional text."""

    def extract_text_from_image(self, image_path: str) -> Dict[str, Any]:
        """
        Extract text and medication information from prescription image.

        Args:
            image_path: Path to the prescription image

        Returns:
            Dictionary containing raw_text and medications list

        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If image format is not supported
        """
        # Validate image file
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        file_ext = os.path.splitext(image_path)[1].lower()
        if file_ext not in Config.SUPPORTED_IMAGE_FORMATS:
            raise ValueError(f"Unsupported image format: {file_ext}")

        try:
            # Load image
            img = Image.open(image_path)

            # Build prompt
            prompt = self._build_vision_prompt()

            # Call Gemini Vision API
            response = self.model.generate_content([prompt, img])

            # Parse JSON response
            response_text = response.text.strip()

            # Remove markdown code blocks if present (FIXED SYNTAX ERRORS HERE)
            if response_text.startswith("```json"):
                response_text = response_text.replace(
                    "```json", "").replace("```", "")
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "")

            # Parse JSON
            result = json.loads(response_text)
            return result

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse JSON response. Error: {e}")
            print(f"Raw response: {response.text}")

            # Fallback: return raw text
            return {
                "raw_text": response.text,
                "medications": [],
                "patient_info": {},
                "special_instructions": ""
            }

        except Exception as e:
            print(f"Error in vision extraction: {e}")
            raise


class PharmacistAgent:
    """
    Standardizes and corrects medication information from OCR output.

    Handles drug name normalization, abbreviation expansion, and
    standardization against known medication databases.
    """

    def __init__(self, drug_aliases: Optional[Dict[str, str]] = None,
                 abbreviation_map: Optional[Dict[str, str]] = None):
        """
        Initialize Pharmacist Agent.

        Args:
            drug_aliases: Custom drug alias mapping
            abbreviation_map: Custom medical abbreviation mapping
        """
        self.drug_aliases = drug_aliases or Config.DRUG_ALIASES
        self.abbreviation_map = abbreviation_map or Config.ABBREVIATION_MAP

    def _normalize_drug_name(self, name: str) -> str:
        """
        Normalize and standardize drug name.

        Args:
            name: Raw drug name from OCR

        Returns:
            Standardized drug name
        """
        if not name:
            return ""

        # Clean special characters
        name_clean = re.sub(r"[^A-Za-z0-9\s-]", "", name).strip()

        # Match against known aliases
        for alias, standard in self.drug_aliases.items():
            if name_clean.lower().startswith(alias.lower()):
                return standard

        return name_clean

    def _expand_abbreviations(self, schedule: str) -> str:
        """
        Expand medical abbreviations in schedule text.

        Args:
            schedule: Schedule string with abbreviations (e.g., "1 tab OD")

        Returns:
            Schedule with expanded abbreviations
        """
        if not schedule:
            return ""

        parts = schedule.split()
        expanded = []

        for part in parts:
            token = part.strip().upper().strip(".,")
            expanded.append(self.abbreviation_map.get(token, part))

        return " ".join(expanded)

    def correct_medications(self, vision_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Correct and standardize medication list from vision output.

        Args:
            vision_output: Raw output from VisionAgent

        Returns:
            Enhanced output with cleaned medications
        """
        medications = vision_output.get("medications", [])
        corrected = []

        for med in medications:
            name = self._normalize_drug_name(med.get("name", "").strip())
            dose = med.get("dose", "").strip()
            schedule = self._expand_abbreviations(
                med.get("schedule", "").strip())

            if name:  # Only add if medication name exists
                corrected.append({
                    "name": name,
                    "dose": dose,
                    "schedule": schedule,
                    "confidence": med.get("confidence", "Low")
                })

        vision_output["medications_clean"] = corrected
        return vision_output


class LinguistAgent:
    """
    Translates medication instructions into conversational Urdu.

    Generates simple, low-literacy-friendly Urdu instructions suitable
    for audio playback to patients.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: str = Config.GEMINI_MODEL):
        """
        Initialize Linguist Agent.

        Args:
            api_key: Gemini API key. If None, reads from environment.
            model_name: Gemini model to use
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not set. Provide via parameter or environment variable."
            )

        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)

    def _build_urdu_prompt(self, medications_clean: List[Dict[str, str]],
                           patient_name: Optional[str] = None) -> str:
        """
        Build prompt for Urdu translation.

        Args:
            medications_clean: List of cleaned medication dictionaries
            patient_name: Optional patient name for personalization

        Returns:
            Prompt string for LLM
        """
        meds_text = "\n".join([
            f"- {m['name']} | {m['dose']} | {m['schedule']}"
            for m in medications_clean
        ])

        patient_greeting = f"Patient name: {patient_name}\n\n" if patient_name else ""

        instruction = f"""You are an assistant that converts medical prescriptions into very simple, conversational Urdu suitable for low-literacy patients.

{patient_greeting}Constraints:
- Use short sentences and everyday Urdu (not formal literary Urdu).
- For each medicine, tell the name, how much to take, when to take it.
- If the schedule contains 'as needed', explain in Urdu when to take it.
- Avoid technical jargon; use simple words like 'subah, dopahar, raat' (صبح، دوپہر، رات) and numerals for doses.
- Make it sound natural and friendly for audio playback.
- Do NOT use any asterisks (*), bold formatting, hashtags (#), or special characters.
- Use plain text only with proper Urdu punctuation.
- Start with a friendly greeting like "Jee, suniye" or "Assalam-o-Alaikum".

Medications:
{meds_text}

Produce ONLY the final spoken Urdu instructions (no English, no JSON, no extra formatting, no asterisks or special characters)."""

        return instruction

    def generate_urdu_text(self, medications_clean: List[Dict[str, str]],
                           patient_name: Optional[str] = None) -> str:
        """
        Generate conversational Urdu instructions.

        Args:
            medications_clean: List of cleaned medication dictionaries
            patient_name: Optional patient name

        Returns:
            Urdu instruction text
        """
        if not medications_clean:
            return "کوئی دوائی نہیں ملی۔"

        prompt = self._build_urdu_prompt(medications_clean, patient_name)

        try:
            # Call Gemini API
            response = self.model.generate_content(prompt)
            urdu_text = response.text.strip()
            return urdu_text

        except Exception as e:
            print(f"Error in Urdu generation: {e}")
            raise


class TTSAgent:
    """
    Text-to-Speech agent using ElevenLabs API.

    Converts Urdu text to high-quality, realistic audio files for patient playback.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize TTS Agent with ElevenLabs.
        """
        self.api_key = api_key or os.getenv(
            "ELEVENLABS_API_KEY") or Config.ELEVENLABS_API_KEY
        if not self.api_key or self.api_key == "your_elevenlabs_api_key_here":
            raise RuntimeError(
                "ELEVENLABS_API_KEY not set. Get your free API key from https://elevenlabs.io"
            )

        self.client = ElevenLabs(api_key=self.api_key)

    def synthesize_urdu(self, urdu_text: str, output_path: str = "output.mp3",
                        voice: str = Config.ELEVENLABS_VOICE,
                        model: str = Config.ELEVENLABS_MODEL,
                        voice_settings: Optional[Dict[str, Any]] = None) -> str:
        """
        Convert Urdu text to speech audio file using ElevenLabs.
        """
        try:
            print(
                f"   Generating audio with voice '{voice}' using model '{model}'...")

            # Use custom voice settings or defaults
            settings = voice_settings or Config.VOICE_SETTINGS

            # Generate audio using the explicit 'text_to_speech.convert' endpoint
            # Note: The parameters here are strictly 'voice_id' and 'model_id'
            audio_generator = self.client.text_to_speech.convert(
                text=urdu_text,
                voice_id=voice,
                model_id=model,
                voice_settings=VoiceSettings(**settings) if settings else None
            )

            # Save audio to file (consumes the generator)
            with open(output_path, 'wb') as f:
                for chunk in audio_generator:
                    if isinstance(chunk, bytes):
                        f.write(chunk)
                    else:
                        f.write(chunk)

            print(f"   ✓ Audio successfully saved to: {output_path}")
            return output_path

        except Exception as e:
            raise RuntimeError(f"ElevenLabs TTS failed: {str(e)}")

    def test_tts(self, test_text: str = "السلام علیکم، یہ ایک ٹیسٹ آڈیو ہے۔",
                 output_path: str = Config.TEST_AUDIO_OUTPUT) -> str:
        """
        Test TTS functionality with sample Urdu text.
        """
        return self.synthesize_urdu(test_text, output_path)


class ManagerAgent:
    """
    Orchestrates the complete MediScribe pipeline.

    Coordinates Vision -> Pharmacist -> Linguist -> TTS workflow.
    """

    def __init__(self, gemini_api_key: Optional[str] = None,
                 elevenlabs_api_key: Optional[str] = None):
        """
        Initialize Manager Agent and all sub-agents.

        Args:
            gemini_api_key: Gemini API key for Vision and Linguist agents
            elevenlabs_api_key: ElevenLabs API key for TTS
        """
        self.gemini_api_key = gemini_api_key or Config.GEMINI_API_KEY
        self.elevenlabs_api_key = elevenlabs_api_key or Config.ELEVENLABS_API_KEY

        os.environ["GEMINI_API_KEY"] = self.gemini_api_key
        os.environ["ELEVENLABS_API_KEY"] = self.elevenlabs_api_key

        print("Initializing agents...")
        self.vision = VisionAgent(self.gemini_api_key,
                                  model_name=Config.GEMINI_MODEL)
        self.pharmacist = PharmacistAgent()
        self.linguist = LinguistAgent(
            self.gemini_api_key, model_name=Config.GEMINI_MODEL)
        self.tts = TTSAgent(self.elevenlabs_api_key)
        print("✓ All agents initialized successfully\n")

    @staticmethod
    def _clean_for_tts(text: str) -> str:
        """
        Remove Markdown-style asterisks and extra whitespace so TTS
        does not read special characters incorrectly.

        Args:
            text: Raw text with potential markdown

        Returns:
            Cleaned text suitable for TTS
        """
        # Remove any number of consecutive '*' characters
        text = re.sub(r"\*+", "", text)
        # Remove other markdown characters
        text = re.sub(r"[#_~`]", "", text)
        # Remove extra newlines but preserve paragraph structure
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Normalize spaces
        text = re.sub(r" +", " ", text)
        # Remove leading/trailing whitespace from each line
        text = "\n".join(line.strip() for line in text.split("\n"))
        return text.strip()

    def process_prescription(
        self,
        image_path: str,
        patient_name: Optional[str] = None,
        synthesize_audio: bool = True,
        audio_output_path: str = Config.DEFAULT_AUDIO_OUTPUT,
        voice: str = Config.ELEVENLABS_VOICE,
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process prescription through complete pipeline.

        Args:
            image_path: Path to prescription image
            patient_name: Optional patient name
            synthesize_audio: Whether to generate audio output
            audio_output_path: Path for audio output file
            voice: ElevenLabs voice to use
            voice_settings: Optional custom voice settings

        Returns:
            Dictionary containing:
                - raw_text: Original extracted text
                - medications_clean: Standardized medication list
                - urdu_text: Cleaned Urdu instructions (no markdown)
                - audio_path: Path to audio file (if synthesize_audio=True)
                - patient_info: Patient information (if extracted)
                - special_instructions: Special notes or warnings

        Raises:
            FileNotFoundError: If image file doesn't exist
            RuntimeError: If any agent fails
        """
        print(f"[1/4] Extracting text from image: {image_path}")
        vision_out = self.vision.extract_text_from_image(image_path)
        print(
            f"   ✓ Extracted {len(vision_out.get('medications', []))} medications")

        print("[2/4] Correcting and standardizing medications...")
        cleaned = self.pharmacist.correct_medications(vision_out)
        print(
            f"   ✓ Standardized {len(cleaned.get('medications_clean', []))} medications")

        print("[3/4] Generating Urdu instructions...")
        urdu_text_raw = self.linguist.generate_urdu_text(
            cleaned.get("medications_clean", []),
            patient_name,
        )

        # Clean Markdown asterisks before TTS
        urdu_text = self._clean_for_tts(urdu_text_raw)
        print(f"   ✓ Generated {len(urdu_text)} characters of Urdu text")

        # Prepare result
        result = {
            "raw_text": vision_out.get("raw_text"),
            "medications_clean": cleaned.get("medications_clean"),
            "urdu_text": urdu_text,
            "patient_info": vision_out.get("patient_info", {}),
            "special_instructions": vision_out.get("special_instructions", "")
        }

        # Step 4: Generate audio (optional)
        if synthesize_audio:
            print(
                f"[4/4] Generating high-quality audio file: {audio_output_path}")
            audio_path = self.tts.synthesize_urdu(
                urdu_text,
                audio_output_path,
                voice=voice,
                voice_settings=voice_settings
            )
            result["audio_path"] = audio_path

        print("\n" + "=" * 60)
        print("✓ Pipeline completed successfully!")
        print("=" * 60)
        return result

# ============================================================================
# Utility Functions
# ============================================================================


def print_results(output: Dict[str, Any]) -> None:
    """
    Pretty print pipeline results.

    Args:
        output: Output dictionary from ManagerAgent
    """
    print("\n" + "=" * 60)
    print("RAW EXTRACTED TEXT")
    print("=" * 60)
    print(output.get("raw_text", "N/A"))

    # Print patient info if available
    patient_info = output.get("patient_info", {})
    if patient_info and any(patient_info.values()):
        print("\n" + "=" * 60)
        print("PATIENT INFORMATION")
        print("=" * 60)
        if patient_info.get("name"):
            print(f"Name: {patient_info['name']}")
        if patient_info.get("age"):
            print(f"Age: {patient_info['age']}")
        if patient_info.get("date"):
            print(f"Date: {patient_info['date']}")

    print("\n" + "=" * 60)
    print("CLEANED MEDICATIONS")
    print("=" * 60)
    medications = output.get("medications_clean", [])
    if medications:
        for i, med in enumerate(medications, 1):
            print(f"\n{i}. {med['name']}")
            print(f"   Dose: {med['dose']}")
            print(f"   Schedule: {med['schedule']}")
            print(f"   Confidence: {med['confidence']}")
    else:
        print("No medications found")

    # Print special instructions if available
    special_instructions = output.get("special_instructions", "")
    if special_instructions:
        print("\n" + "=" * 60)
        print("SPECIAL INSTRUCTIONS")
        print("=" * 60)
        print(special_instructions)

    print("\n" + "=" * 60)
    print("URDU INSTRUCTIONS")
    print("=" * 60)
    print(output.get("urdu_text", "N/A"))

    if "audio_path" in output:
        print("\n" + "=" * 60)
        print(f"✓ Audio saved to: {output['audio_path']}")
        print("=" * 60)


def validate_setup() -> bool:
    """
    Validate that all required API keys and dependencies are configured.

    Returns:
        True if setup is valid, False otherwise
    """
    issues = []

    # Check Gemini API key
    if not Config.GEMINI_API_KEY or Config.GEMINI_API_KEY == "":
        issues.append("❌ GEMINI_API_KEY is not set")
    else:
        print("✓ Gemini API key configured")

    # Check ElevenLabs API key
    if not Config.ELEVENLABS_API_KEY or Config.ELEVENLABS_API_KEY == "your_elevenlabs_api_key_here":
        issues.append("❌ ELEVENLABS_API_KEY is not set")
    else:
        print("✓ ElevenLabs API key configured")

    # Check required packages
    try:
        import google.generativeai
        print("✓ google-generativeai package installed")
    except ImportError:
        issues.append(
            "❌ google-generativeai package not installed. Run: pip install google-generativeai")

    try:
        from elevenlabs import ElevenLabs
        print("✓ elevenlabs package installed")
    except ImportError:
        issues.append(
            "❌ elevenlabs package not installed. Run: pip install elevenlabs")

    try:
        from PIL import Image
        print("✓ Pillow package installed")
    except ImportError:
        issues.append(
            "❌ Pillow package not installed. Run: pip install Pillow")

    if issues:
        print("\n" + "=" * 60)
        print("SETUP ISSUES FOUND:")
        print("=" * 60)
        for issue in issues:
            print(issue)
        print("\nPlease resolve these issues before running the pipeline.")
        return False

    print("\n✓ All dependencies and API keys configured correctly!\n")
    return True

# ============================================================================
# Main Execution
# ============================================================================


def main():
    """Main execution function for the MediScribe pipeline."""

    print("=" * 60)
    print("MediScribe Agents Pipeline v2.0")
    print("Multi-Agent Medical Prescription Processing System")
    print("=" * 60 + "\n")

    # Validate setup
    print("Validating setup...")
    if not validate_setup():
        return

    # Test TTS functionality
    print("\nTesting ElevenLabs TTS functionality...")
    try:
        tts_agent = TTSAgent()
        test_audio = tts_agent.test_tts()
        print(f"✓ Test audio saved: {test_audio}\n")
    except RuntimeError as e:
        print(f"⚠ TTS test failed: {e}")
        print("Please check your ElevenLabs API key and try again.\n")
        return

    # Configure prescription image path
    image_path = r"C:\Users\abdre\Downloads\archive\data\9.jpg"

    # Check if image exists
    if not os.path.exists(image_path):
        print(f"❌ Error: Image file not found at: {image_path}")
        print("Please update the image_path variable with a valid prescription image.")
        return

    # Initialize manager and process prescription
    print("=" * 60)
    print("PROCESSING PRESCRIPTION")
    print("=" * 60 + "\n")

    try:
        manager = ManagerAgent()

        print(f"Processing prescription: {image_path}\n")
        output = manager.process_prescription(
            image_path=image_path,
            patient_name=None,
            synthesize_audio=True,
            voice=Config.ELEVENLABS_VOICE,  # <--- CHANGED: Use the ID from Config
            voice_settings=None
        )

        # Display results
        print_results(output)

        print("\n" + "=" * 60)
        print("PIPELINE EXECUTION SUMMARY")
        print("=" * 60)
        print(f"✓ Image processed: {image_path}")
        print(
            f"✓ Medications extracted: {len(output.get('medications_clean', []))}")
        print(
            f"✓ Urdu text generated: {len(output.get('urdu_text', ''))} characters")
        if output.get('audio_path'):
            print(f"✓ Audio file created: {output['audio_path']}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error during pipeline execution: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
