# MediScribe

MediScribe is a multi-agent system for processing medical prescriptions with OCR, correction, translation to Urdu, and high-quality text-to-speech generation using Gemini AI and ElevenLabs.

## Features
- 📸 Prescription image text extraction (OCR) using Gemini Vision
- 💊 Medication name correction and standardization
- 🌐 Translation to Urdu with proper medical terminology
- 🔊 High-quality Urdu text-to-speech using ElevenLabs
- 📱 Web-based interface for easy prescription management

## Setup

### 1. Database (MySQL Workbench)
Run `database_setup.sql`

### 2. Backend
```bash
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

**Note:** Make sure to configure your API keys in `backend/.env`:
- `GEMINI_API_KEY` - Google Gemini API key
- `ELEVENLABS_API_KEY` - ElevenLabs API key

### 3. Frontend
```bash
cd frontend
npm install
npm start
```

Done. Backend: http://localhost:5000 | Frontend: http://localhost:3000

## Technologies Used
- **Backend:** Flask, Google Gemini AI, ElevenLabs TTS, SQLAlchemy
- **Frontend:** React
- **Database:** MySQL
