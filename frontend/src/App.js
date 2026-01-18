import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = 'http://localhost:5000/api';

function App() {
  // Helper function to format dates
  const formatDateTime = (dateString) => {
    const date = new Date(dateString);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const day = date.getDate();
    const month = months[date.getMonth()];
    const year = date.getFullYear();
    let hours = date.getHours();
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12 || 12;
    return `${day} ${month} ${year} - ${hours}:${minutes} ${ampm}`;
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const day = date.getDate();
    const month = months[date.getMonth()];
    const year = date.getFullYear();
    return `${day} ${month},${year}`;
  };

  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [prescriptions, setPrescriptions] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [processingStage, setProcessingStage] = useState('');
  const [showHistory, setShowHistory] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [currentView, setCurrentView] = useState('home'); // 'home', 'library', 'audio'

  useEffect(() => {
    loadPrescriptions();
  }, []);

  useEffect(() => {
    if (darkMode) {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
  }, [darkMode]);

  const loadPrescriptions = async () => {
    try {
      const response = await fetch(`${API_BASE}/prescriptions`);
      const data = await response.json();
      setPrescriptions(data.prescriptions || []);
    } catch (err) {
      console.error('Failed to load prescriptions:', err);
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreview(URL.createObjectURL(file));
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) {
      setSelectedFile(file);
      setPreview(URL.createObjectURL(file));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    setLoading(true);
    setError('');
    setSuccess('');
    setResult(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      // Simulate processing stages
      setProcessingStage('Extracting text from prescription...');
      await new Promise(resolve => setTimeout(resolve, 800));
      
      setProcessingStage('Understanding medicines...');
      await new Promise(resolve => setTimeout(resolve, 800));
      
      setProcessingStage('Generating Urdu instructions...');
      await new Promise(resolve => setTimeout(resolve, 800));
      
      setProcessingStage('Creating audio...');

      const response = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Upload failed');
      }

      setProcessingStage('');
      setResult(data.prescription);
      loadPrescriptions();
      
      // Reset form
      setSelectedFile(null);
      setPreview(null);
    } catch (err) {
      setError(err.message);
      setProcessingStage('');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setSuccess('Copied to clipboard!');
    setTimeout(() => setSuccess(''), 2000);
  };

  const downloadAudio = () => {
    if (result?.audio_path) {
      const link = document.createElement('a');
      link.href = `${API_BASE}/audio/${result.audio_path}`;
      link.download = 'prescription_audio.mp3';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const startNewChat = () => {
    setResult(null);
    setSelectedFile(null);
    setPreview(null);
    setError('');
    setSuccess('');
    setCurrentView('home');
  };

  const deletePrescription = async (uniqueId) => {
    if (!window.confirm('Delete this prescription?')) return;

    try {
      const response = await fetch(`${API_BASE}/prescriptions/${uniqueId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        setSuccess('Prescription deleted');
        loadPrescriptions();
        setTimeout(() => setSuccess(''), 3000);
      }
    } catch (err) {
      setError('Failed to delete');
    }
  };

  return (
    <div className="App">
      {/* Sidebar */}
      <div className={`sidebar ${showHistory ? 'open' : ''}`}>
        <div className="sidebar-header">
          {showHistory && <img src="/logo.png" alt="MediScribe Logo" className="sidebar-logo" />}
          <button className="sidebar-toggle-btn" onClick={() => setShowHistory(!showHistory)} title={showHistory ? 'Close sidebar' : 'Open sidebar'}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {showHistory ? (
                <path d="M15 18l-6-6 6-6" />
              ) : (
                <path d="M9 18l6-6-6-6" />
              )}
            </svg>
          </button>
        </div>

        {!showHistory && (
          <>
            <div className="sidebar-icons">
              <button className="sidebar-icon-btn" onClick={startNewChat} title="New Chat">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 5v14M5 12h14" />
                </svg>
              </button>
              <button className="sidebar-icon-btn" onClick={() => setCurrentView('library')} title="Library">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                </svg>
              </button>
              <button className="sidebar-icon-btn" onClick={() => setCurrentView('audio')} title="Audio">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                </svg>
              </button>
            </div>
          </>
        )}

        {showHistory && (
          <>
            <div className="sidebar-menu">
              <button className="sidebar-menu-btn" onClick={startNewChat}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 5v14M5 12h14" />
                </svg>
                <span>New Chat</span>
              </button>
              <button className="sidebar-menu-btn" onClick={() => setCurrentView('library')}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                </svg>
                <span>Library</span>
              </button>
              <button className="sidebar-menu-btn" onClick={() => setCurrentView('audio')}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                </svg>
                <span>Audio</span>
              </button>
            </div>

            <div className="sidebar-divider"></div>

            <div className="history-list">
              <h3 className="history-title">History</h3>
              {prescriptions.length > 0 ? (
                prescriptions.map((prescription) => (
                  <div 
                    key={prescription.id} 
                    className="history-item"
                    onClick={() => {
                      setResult(prescription);
                      setCurrentView('home');
                    }}
                  >
                    <div className="history-item-title">Prescription {prescription.id}</div>
                    <div className="history-item-date">
                      {formatDate(prescription.created_at)}
                    </div>
                  </div>
                ))
              ) : (
                <p className="no-history">No history yet</p>
              )}
            </div>
          </>
        )}
      </div>

      {/* Main Content */}
      <div className="main-container">
        {/* Top Bar */}
        <div className={`top-bar ${showHistory ? 'sidebar-open' : ''}`}>
          <div className="app-title">
            {/* <img src="/logo.png" alt="MediScribe Logo" className="app-logo" /> */}
            <div className="title-text">
              <h1>MediScribe<span className="urdu-label">Urdu</span></h1>
              {/* <p>AI-Powered Prescription Analysis & Urdu Translation</p> */}
            </div>
          </div>
          <button className="theme-toggle-topbar" onClick={() => setDarkMode(!darkMode)} title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {darkMode ? (
                <>
                  <circle cx="12" cy="12" r="5" />
                  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
                </>
              ) : (
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              )}
            </svg>
          </button>
        </div>

        {/* Content Area */}
        <div className="content-area">
          {currentView === 'library' ? (
            // Library View
            <div className="library-view">
              {/* <h2 className="view-title">Prescription Library</h2> */}
              <div className="library-grid">
                {prescriptions.length > 0 ? (
                  prescriptions.map((prescription) => (
                    <div key={prescription.id} className="library-card">
                      <div className="library-card-header">
                        <h3>Prescription {prescription.id}</h3>
                        <span className={`status-badge ${prescription.status}`}>
                          {prescription.status}
                        </span>
                      </div>
                      <div className="library-card-content">
                        <p className="library-date">
                          {formatDateTime(prescription.created_at)}
                        </p>
                        {prescription.image_path && (
                          <img 
                            src={`${API_BASE}/image/${prescription.image_path}`}
                            alt="Prescription"
                            className="library-image"
                          />
                        )}
                        <p className="library-text">{prescription.raw_text?.substring(0, 100)}...</p>
                      </div>
                      <button 
                        className="library-view-btn"
                        onClick={() => {
                          setResult(prescription);
                          setCurrentView('home');
                        }}
                      >
                        View Details
                      </button>
                    </div>
                  ))
                ) : (
                  <p className="no-data">No prescriptions in library</p>
                )}
              </div>
            </div>
          ) : currentView === 'audio' ? (
            // Audio View
            <div className="audio-view">
              {/* <h2 className="view-title">Audio Library</h2> */}
              <div className="audio-list">
                {prescriptions.filter(p => p.audio_path).length > 0 ? (
                  prescriptions.filter(p => p.audio_path).map((prescription) => (
                    <div key={prescription.id} className="audio-item">
                      <div className="audio-item-info">
                        <h3>Prescription {prescription.id}</h3>
                        <p>{formatDateTime(prescription.created_at)}</p>
                      </div>
                      <audio 
                        controls 
                        className="audio-player-list"
                        src={`${API_BASE}/audio/${prescription.audio_path}`}
                      />
                      {/* <button 
                        className="audio-download-btn"
                        onClick={() => {
                          const link = document.createElement('a');
                          link.href = `${API_BASE}/audio/${prescription.audio_path}`;
                          link.download = `prescription_${prescription.id}_audio.mp3`;
                          document.body.appendChild(link);
                          link.click();
                          document.body.removeChild(link);
                        }}
                      >
                        Download
                      </button> */}
                    </div>
                  ))
                ) : (
                  <p className="no-data">No audio files available</p>
                )}
              </div>
            </div>
          ) : !result && !loading ? (
            // Home Screen - Upload Area
            <div className="hero-section">
              <div className="upload-container">
                <div 
                  className="upload-box"
                  onClick={() => document.getElementById('fileInput').click()}
                  onDrop={handleDrop}
                  onDragOver={(e) => e.preventDefault()}
                >
                  <img src="/upload.png" alt="MediScribe" className="upload-logo" />
                  <h2>Upload Prescription</h2>
                  <p className="upload-text">Click to upload or drag and drop</p>
                  <p className="upload-hint">Image, PDF or handwritten prescriptions allowed</p>
                </div>

                <input
                  id="fileInput"
                  type="file"
                  accept="image/*"
                  onChange={handleFileChange}
                  style={{ display: 'none' }}
                />

                {preview && (
                  <div className="preview-section">
                    <img src={preview} alt="Preview" className="preview-img" />
                    <button className="btn-primary" onClick={handleSubmit}>
                      Analyze Prescription
                    </button>
                  </div>
                )}
              </div>
            </div>
          ) : loading ? (
            // Processing Screen
            <div className="processing-screen">
              <div className="loader-animation">
                <div className="pulse"></div>
              </div>
              <p className="processing-text">{processingStage}</p>
            </div>
          ) : (
            // Results Screen - AI Output
            <div className="results-container">
              <div className="results-content">
                {/* Audio Player */}
                {result.audio_path && (
                  <div className="result-card">
                    <div className="result-card-header">
                      <h3>Audio Instructions</h3>
                      <button className="icon-btn" onClick={downloadAudio} title="Download Audio">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                          <polyline points="7 10 12 15 17 10"/>
                          <line x1="12" y1="15" x2="12" y2="3"/>
                        </svg>
                      </button>
                    </div>
                    <div className="audio-player-wrapper">
                      <audio 
                        controls
                        className="audio-player-minimal"
                        src={`${API_BASE}/audio/${result.audio_path}`}
                      />
                    </div>
                  </div>
                )}

                {/* Extracted Text */}
                <div className="result-card">
                  <div className="result-card-header">
                    <h3>Extracted Text</h3>
                    <button className="icon-btn" onClick={() => copyToClipboard(result.raw_text)} title="Copy to clipboard">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                      </svg>
                    </button>
                  </div>
                  <div className="result-text-content">
                    {result.raw_text}
                  </div>
                </div>

                {/* Urdu Instructions */}
                <div className="result-card urdu-result-card">
                  <div className="result-card-header">
                    <h3>Urdu Instructions</h3>
                    <button className="icon-btn" onClick={() => copyToClipboard(result.urdu_text)} title="Copy to clipboard">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                      </svg>
                    </button>
                  </div>
                  <div className="result-urdu-content">
                    {result.urdu_text}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Error/Success Messages */}
        {error && (
          <div className="toast toast-error">
            {error}
          </div>
        )}
        {success && (
          <div className="toast toast-success">
            {success}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
