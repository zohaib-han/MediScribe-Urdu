"""
MediScribe Backend API
Flask-based REST API for prescription processing
"""

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import sys
from werkzeug.utils import secure_filename
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from NLP_proj import ManagerAgent

# Initialize Flask app
app = Flask(__name__, static_folder='frontend/build', static_url_path='/')
CORS(app, supports_credentials=True)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['AUDIO_FOLDER'] = os.path.join(os.path.dirname(__file__), 'audio_outputs')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

# Initialize database
db = SQLAlchemy(app)
with app.app_context():
    db.create_all()

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['AUDIO_FOLDER'], exist_ok=True)

# Initialize pipeline
manager = ManagerAgent()


# ==================== Database Models ====================
class Prescription(db.Model):
    """Prescription model"""
    id = db.Column(db.Integer, primary_key=True)
    unique_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    image_path = db.Column(db.String(255), nullable=False)
    raw_text = db.Column(db.Text, nullable=True)
    urdu_text = db.Column(db.Text, nullable=True)
    audio_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, processed, error
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    medications = db.relationship('Medication', backref='prescription', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'unique_id': self.unique_id,
            'image_path': self.image_path,
            'raw_text': self.raw_text,
            'urdu_text': self.urdu_text,
            'audio_path': self.audio_path,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),
            'medications': [med.to_dict() for med in self.medications]
        }


class Medication(db.Model):
    """Medication model"""
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescription.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    dose = db.Column(db.String(100), nullable=True)
    schedule = db.Column(db.String(200), nullable=True)
    confidence = db.Column(db.String(20), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'dose': self.dose,
            'schedule': self.schedule,
            'confidence': self.confidence
        }


# ==================== Helper Functions ====================
def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# ==================== API Endpoints ====================
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'MediScribe API is running'}), 200


@app.route('/api/upload', methods=['POST'])
def upload_prescription():
    """Upload and process prescription image"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: png, jpg, jpeg, webp, gif'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Create prescription record
        prescription = Prescription(
            image_path=unique_filename,
            status='pending'
        )
        db.session.add(prescription)
        db.session.commit()
        
        # Process prescription
        try:
            audio_filename = f"{prescription.unique_id}.mp3"
            audio_path = os.path.join(app.config['AUDIO_FOLDER'], audio_filename)
            
            # Run pipeline with the new NLP_proj ManagerAgent
            result = manager.process_prescription(
                image_path=file_path,
                patient_name=None,
                synthesize_audio=True,
                audio_output_path=audio_path
            )
            
            # Debug: Print what we got
            print(f"DEBUG - Raw text: {result.get('raw_text')}")
            print(f"DEBUG - Urdu text: {result.get('urdu_text')}")
            print(f"DEBUG - Urdu text type: {type(result.get('urdu_text'))}")
            
            # Update prescription with results
            prescription.raw_text = result.get('raw_text')
            prescription.urdu_text = result.get('urdu_text')
            prescription.audio_path = audio_filename
            prescription.status = 'processed'
            
            # Add medications
            for med_data in result.get('medications_clean', []):
                medication = Medication(
                    prescription_id=prescription.id,
                    name=med_data.get('name'),
                    dose=med_data.get('dose'),
                    schedule=med_data.get('schedule'),
                    confidence=med_data.get('confidence')
                )
                db.session.add(medication)
            
            db.session.commit()
            
            return jsonify({
                'message': 'Prescription processed successfully',
                'prescription': prescription.to_dict()
            }), 201
            
        except Exception as e:
            prescription.status = 'error'
            prescription.error_message = str(e)
            db.session.commit()
            return jsonify({'error': f'Processing failed: {str(e)}'}), 500
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/prescriptions', methods=['GET'])
def get_prescriptions():
    """Get all prescriptions"""
    try:
        prescriptions = Prescription.query.order_by(Prescription.created_at.desc()).all()
        return jsonify({
            'prescriptions': [p.to_dict() for p in prescriptions],
            'count': len(prescriptions)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/prescriptions/<unique_id>', methods=['GET'])
def get_prescription(unique_id):
    """Get specific prescription by unique_id"""
    try:
        prescription = Prescription.query.filter_by(unique_id=unique_id).first()
        if not prescription:
            return jsonify({'error': 'Prescription not found'}), 404
        return jsonify({'prescription': prescription.to_dict()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/prescriptions/<unique_id>', methods=['DELETE'])
def delete_prescription(unique_id):
    """Delete prescription"""
    try:
        prescription = Prescription.query.filter_by(unique_id=unique_id).first()
        if not prescription:
            return jsonify({'error': 'Prescription not found'}), 404
        
        # Delete files
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], prescription.image_path)
        if os.path.exists(image_path):
            os.remove(image_path)
        
        if prescription.audio_path:
            audio_path = os.path.join(app.config['AUDIO_FOLDER'], prescription.audio_path)
            if os.path.exists(audio_path):
                os.remove(audio_path)
        
        db.session.delete(prescription)
        db.session.commit()
        
        return jsonify({'message': 'Prescription deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/audio/<filename>', methods=['GET'])
def get_audio(filename):
    """Serve audio file"""
    try:
        audio_path = os.path.join(app.config['AUDIO_FOLDER'], filename)
        if not os.path.exists(audio_path):
            return jsonify({'error': 'Audio file not found'}), 404
        return send_file(audio_path, mimetype='audio/mpeg')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/image/<filename>', methods=['GET'])
def get_image(filename):
    """Serve prescription image"""
    try:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(image_path):
            return jsonify({'error': 'Image file not found'}), 404
        return send_file(image_path)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== Database Initialization ====================
def init_db():
    """Initialize database"""
    with app.app_context():
        db.create_all()
        print("✓ Database initialized successfully")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == "__main__":
    print("MediScribe API running")
