// App.jsx
import React, { useState } from 'react';
import axios from 'axios';
import './App.css';
import './SOS.css';
import Dashboard from './Dashboard';

function App() {
  const [view, setView] = useState("user");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [passwordInput, setPasswordInput] = useState("");

  const [status, setStatus] = useState("Ready");
  const [isRecording, setIsRecording] = useState(false);
  const [result, setResult] = useState(null);
  const [textMessage, setTextMessage] = useState("");

  const handleSOS = async () => {
    setIsRecording(true);
    setStatus("Getting Location...");

    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser");
      setIsRecording(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        startRecording(latitude, longitude);
      },
      () => {
        setStatus("Error: Location Access Denied");
        setIsRecording(false);
      }
    );
  };

  const startRecording = async (lat, lon) => {
    setStatus("🎙️ Recording Audio (3s)...");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      const audioChunks = [];

      mediaRecorder.ondataavailable = (event) => audioChunks.push(event.data);

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        await sendAlert(lat, lon, audioBlob);
      };

      mediaRecorder.start();
      setTimeout(() => {
        mediaRecorder.stop();
        setIsRecording(false);
      }, 3000);
    } catch (err) {
      setStatus("Error: Mic Access Denied");
      setIsRecording(false);
    }
  };

  const sendAlert = async (lat, lon, audioBlob) => {
    setStatus("📡 Sending Alert to AI...");
    const formData = new FormData();
    formData.append("audio_file", audioBlob, "sos_audio.wav");
    formData.append("location_data", `${lat},${lon}`);
    formData.append("text_message", textMessage || "React App SOS Triggered");

    try {
      const response = await axios.post(
        "http://127.0.0.1:8000/api/v1/sos_alert",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setResult(response.data);
      setStatus("✅ Help is on the way!");
    } catch (error) {
      console.error(error);
      setStatus("❌ Server Error");
    }
  };

  const handleLogin = () => {
    if (passwordInput === "police123") {
      setIsAuthenticated(true);
      setView("admin");
    } else {
      alert("Wrong Password!");
    }
  };

  // LOGIN SCREEN
  if (view === "admin" && !isAuthenticated) {
    return (
      <div className="login-screen">
        <div className="login-card">
          <div className="login-emoji">👮</div>
          <h2 className="login-title">Restricted Access</h2>
          <p className="login-subtitle">Enter your responder credentials</p>

          <input
            type="password"
            value={passwordInput}
            onChange={(e) => setPasswordInput(e.target.value)}
            placeholder="Password"
            onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
            className="login-input"
          />

          <button onClick={handleLogin} className="login-button">
            Login
          </button>

          <button
            onClick={() => setView("user")}
            className="login-back-btn"
          >
            ← Back to User App
          </button>
        </div>
      </div>
    );
  }

  // ADMIN DASHBOARD
  if (view === "admin" && isAuthenticated) {
    return (
      <Dashboard
        onLogout={() => {
          setIsAuthenticated(false);
          setView("user");
        }}
      />
    );
  }

  // USER SOS SCREEN
  return (
    <div className="sos-screen">
      <button
        onClick={() => setView("admin")}
        className="sos-admin-btn"
      >
        👮 Dashboard
      </button>

      <div className="sos-content">
        <h1 className="sos-title">Emergency SOS</h1>
        <p className="sos-subtitle">Tap below to trigger AI assistance</p>

        <textarea
          className="sos-text-input"
          value={textMessage}
          onChange={(e) => setTextMessage(e.target.value)}
          placeholder="Optional: Describe what's happening..."
          disabled={isRecording}
        />

        <div className="sos-main-wrapper">
          <button
            onClick={handleSOS}
            disabled={isRecording}
            className={`sos-main-btn ${isRecording ? 'sos-main-btn-recording' : ''}`}
          >
            {isRecording ? "..." : "SOS"}
          </button>

          {isRecording && <div className="sos-pulse-ring" />}
        </div>

        <h3 className="sos-status">{status}</h3>

        {result && (
          <div className="result-card">
            <div className="result-grid">
              <div className="result-block">
                <div className="result-label">Severity Level</div>
                <div
                  className={`result-severity ${
                    result.severity === 'High'
                      ? 'severity-high'
                      : 'severity-low'
                  }`}
                >
                  {result.severity}
                </div>
              </div>

              <div className="result-block">
                <div className="result-label">Confidence</div>
                <div className="result-confidence">
                  {(result.confidence * 100).toFixed(1)}%
                </div>
              </div>

              <div className="result-block result-block-full">
                <div className="result-label">Incident ID</div>
                <div className="result-incident">
                  #{result.details?.incident_id || "N/A"}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
