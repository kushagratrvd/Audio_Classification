import os
import shutil
import uuid
import datetime
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Optional
from fastapi import Depends, status, Header


# We wrap this in try-except so the server doesn't crash if libraries are missing during setup
try:
    from risk_scorer import calculate_risk_score
except ImportError as e:
    print(f"Warning: AI modules not found ({e}). AI scoring will be simulated.")
    def calculate_risk_score(audio_file_path, text_input):
        return "High", 0.95, {"error": "AI module missing, simulated response"}

# This creates a file 'safety.db' in your folder. No installation needed.
SQLALCHEMY_DATABASE_URL = "sqlite:///./safety.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define the Table
class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    latitude = Column(String)
    longitude = Column(String)
    severity = Column(String) # High, Medium, Low
    details = Column(String)  # JSON string or text summary

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

# Create the tables
Base.metadata.create_all(bind=engine)

# Run this once on startup
def create_default_admin():
    db = SessionLocal()
    if not db.query(Admin).filter(Admin.username == "admin").first():
        print("Creating default admin user...")
        # In real life, use bcrypt to hash this password
        default_admin = Admin(username="admin", password="police123")
        db.add(default_admin)
        db.commit()
    db.close()

create_default_admin()

# This function runs before the Dashboard route. 
# If the "admin-secret" header is wrong, it blocks the request.
def verify_admin(admin_secret: str = Header(None)):
    if admin_secret != "police123": # Simple check for prototype
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

app = FastAPI(
    title="AI Emergency Assistance API",
    description="FastAPI backend with combined Audio and Text Risk Scoring."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (React, Mobile, etc.)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (POST, GET, etc.)
    allow_headers=["*"],  # Allows all headers
)

class AdminUser(BaseModel):
    username: str
    password: str

@app.post("/api/v1/login")
def login(creds: AdminUser):
    db = SessionLocal()

    user = db.query(Admin).filter(Admin.username == creds.username).first()
    db.close()

    if not user or user.password != creds.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Return the 'token' (in this simple case, the password itself serves as the key)
    return {"status": "success", "token": user.password}

# --- Configuration ---
# Directory to temporarily store the uploaded audio files
UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Pydantic Data Model for Response ---
# Defines the structured output the API will send back
class RiskScoreOut(BaseModel):
    severity: str
    confidence: float
    message: str
    details: dict

def simulate_email_alert(email_to, severity, location, link):
    print("\n" + "="*40)
    print(f"📧 [SIMULATION] SENDING EMAIL TO: {email_to}")
    print(f"🚨 SUBJECT: SOS ALERT - Severity {severity}")
    print(f"📍 LOCATION: {location}")
    print(f"🔗 MAP LINK: {link}")
    print("="*40 + "\n")

# --- API Endpoint: SOS Alert ---
@app.post("/api/v1/sos_alert", response_model=RiskScoreOut)
async def sos_alert_endpoint(
    # UploadFile handles the binary audio file upload
    audio_file: Optional[UploadFile] = File(None, description="Optional 3-second audio clip"),
    # Form handles simple key-value fields like text/location
    location_data: str = Form(..., description="GPS location data (lat, lon)"),
    text_message: Optional[str] = Form(None, description="Optional text message from user")
):
    """
    Receives an SOS alert, analyzes audio and text, and returns a risk score.
    """
    audio_path = None
    
    try:
        # 1. Save the uploaded audio file (if provided)
        if audio_file and audio_file.filename:
            # Generate a unique filename to prevent conflicts
            ext = os.path.splitext(audio_file.filename)[1] or ".webm"
            unique_filename = f"{uuid.uuid4()}{ext}"
            audio_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            # Save the file using shutil.copyfileobj for efficiency
            with open(audio_path, "wb") as buffer:
                shutil.copyfileobj(audio_file.file, buffer)
        
        # 2. RUN AI-BASED RISK SCORING (Calls the function in risk_scorer.py)
        severity, confidence, details = calculate_risk_score(
            audio_file_path=audio_path,
            text_input=text_message
        )

        # --- SAVE TO DB ---
        db = SessionLocal()
        new_incident = Incident(
            latitude=location_data.split(',')[0] if ',' in location_data else "0.0",
            longitude=location_data.split(',')[1] if ',' in location_data else "0.0",
            severity=severity,
            details=str(details)
        )
        db.add(new_incident)
        db.commit()
        db.refresh(new_incident)
        db.close()

        if severity == "High" or severity == "Medium":
            google_maps_link = f"https://www.google.com/maps/search/?api=1&query={new_incident.latitude},{new_incident.longitude}"
            simulate_email_alert("police@emergency.com", severity, location_data, google_maps_link)

        # 3. Construct Response
        return RiskScoreOut(
            severity=severity,
            confidence=confidence,
            message=f"Alert received and classified as {severity}.",
            details=details
        )
        
    except Exception as e:
        print(f"Processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error during risk scoring: {e}")
        
    finally:
        # 4. Clean up: ALWAYS delete the temporary audio file
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


@app.get("/api/v1/incidents", dependencies=[Depends(verify_admin)])
def get_incidents():
    db = SessionLocal()
    incidents = db.query(Incident).all()
    db.close()
    return incidents

# --- Run the application (Local Development) ---
#if __name__ == "__main__":
    #import uvicorn
    # This command runs your API locally (on http://127.0.0.1:8000)
    #uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)