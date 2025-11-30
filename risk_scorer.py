import joblib
import librosa
import shutil
import numpy as np
import os
from transformers import pipeline
from typing import Optional, Tuple, Dict
import subprocess

# --- Global Configurations (Must match train_model.py) ---
TARGET_DURATION = 3.0 
N_MFCC = 40
SAMPLE_RATE = 22050
DISTRESS_AUDIO_LABELS = ['fear', 'anger', 'disgust']
DISTRESS_TEXT_LABELS = ['NEGATIVE'] 

# --- Load Assets ---
try:
    # Load the trained model and scaler
    AUDIO_MODEL = joblib.load('audio_distress_model.joblib')
    FEATURE_SCALER = joblib.load('feature_scaler.joblib')
except Exception as e:
    print(f"Error loading AI assets: {e}")
    AUDIO_MODEL = None
    FEATURE_SCALER = None

# Initialize Hugging Face Text Classifier Pipeline
try:
    TEXT_CLASSIFIER = pipeline(
        "zero-shot-classification", 
        model="facebook/bart-large-mnli"
    )
    # Define text labels for zero-shot classification
    TEXT_CANDIDATE_LABELS = ["distress", "safety check", "neutral"]
except Exception as e:
    print(f"Error loading Hugging Face pipeline: {e}")
    TEXT_CLASSIFIER = None


def convert_to_wav(input_path, output_path="converted.wav"):
    try:
        # If ffmpeg is on PATH, use that.
        ffmpeg_cmd = shutil.which("ffmpeg")

        result = subprocess.run([
            ffmpeg_cmd, "-y",
            "-i", input_path,
            "-ar", str(SAMPLE_RATE),
            "-ac", "1",
            output_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            print("FFmpeg error:", result.stderr)
            return None

        return output_path

    except Exception as e:
        print("FFmpeg conversion failed:", e)
        return None

# --- Feature Extraction Function ---
def extract_features_for_inference(file_path: str, sample_rate: int = SAMPLE_RATE) -> Optional[np.ndarray]:
    """Extracts features from a single new audio file."""
    try:
        # Convert WebM/OGG → WAV
        wav_path = convert_to_wav(file_path)
        if not wav_path:
            print("Audio conversion failed")
            return None

        audio, sr = librosa.load(wav_path, sr=sample_rate)
        # Pad or trim audio to exactly TARGET_DURATION
        required_len = int(TARGET_DURATION * sample_rate)
        if len(audio) < required_len:
            audio = np.pad(audio, (0, required_len - len(audio)))
        else:
            audio = audio[:required_len]
        
        # 1. MFCCs
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=N_MFCC)
        mfccs_mean = np.mean(mfccs.T, axis=0)
        mfccs_stdev = np.std(mfccs.T, axis=0)
        
        # 2. Chroma
        chroma = librosa.feature.chroma_stft(y=audio, sr=sr)
        chroma_mean = np.mean(chroma.T, axis=0)
        chroma_stdev = np.std(chroma.T, axis=0)

        # 3. Mel Spectrogram
        mel = librosa.feature.melspectrogram(y=audio, sr=sr)
        mel_mean = np.mean(mel.T, axis=0)
        mel_stdev = np.std(mel.T, axis=0)
        
        feature_vector = np.hstack([
            mfccs_mean, mfccs_stdev, 
            chroma_mean, chroma_stdev, 
            mel_mean, mel_stdev
        ])
        
        # Reshape for single prediction (1 sample, N features)
        return feature_vector.reshape(1, -1)
        
    except Exception as e:
        # If audio fails (e.g., missing FFmpeg), return None so we can fallback to text
        print(f"Feature extraction failed: {e}")
        return None

# --- Core Scoring Function (Called by FastAPI) ---
def calculate_risk_score(audio_file_path: Optional[str] = None, text_input: Optional[str] = None) -> Tuple[str, float, Dict]:
    """
    Calculates the final severity score based on audio and optional text confidence.
    Returns: (Severity_Level, Final_Confidence, Details)
    """
    
    audio_confidence = 0.0
    text_confidence = 0.0
    audio_emotion = "N/A"
    
    details = {}

    # 1. AUDIO CLASSIFICATION
    if audio_file_path and AUDIO_MODEL and FEATURE_SCALER:
        features = extract_features_for_inference(audio_file_path)
        
        if features is not None:
            # Scale features
            features_scaled = FEATURE_SCALER.transform(features)
            # Get probabilities
            probabilities = AUDIO_MODEL.predict_proba(features_scaled)[0]
            class_labels = AUDIO_MODEL.classes_
            
            # Find max distress confidence
            for label, proba in zip(class_labels, probabilities):
                if label in DISTRESS_AUDIO_LABELS:
                    if proba > audio_confidence:
                        audio_confidence = proba
                        audio_emotion = label
        else:
            details["audio_error"] = "Audio processing failed (Codec/FFmpeg issue)"

    # 2. TEXT CLASSIFICATION
    if text_input and TEXT_CLASSIFIER:
        try:
            results = TEXT_CLASSIFIER(text_input, TEXT_CANDIDATE_LABELS, multi_label=False)
            if 'distress' in results['labels']:
                distress_index = results['labels'].index('distress')
                text_confidence = results['scores'][distress_index]
        except Exception as e:
            print(f"Text analysis error: {e}")

    # 3. FINAL CONFIDENCE-BASED RISK MAPPING
    # Use the max confidence from the two inputs
    final_confidence = max(audio_confidence, text_confidence)

    # Define thresholds
    if final_confidence >= 0.85:
        severity = "High"     # Changed from "HIGH_RISK" to match Frontend
    elif final_confidence >= 0.50:
        severity = "Medium"   # Changed from "MEDIUM_RISK" to match Frontend
    else:
        severity = "Low"      # Changed from "LOW_RISK" to match Frontend

    # Update details
    details.update({
        "audio_confidence": float(audio_confidence),
        "audio_emotion": audio_emotion,
        "text_confidence_distress": float(text_confidence)
    })

    return severity, float(final_confidence), details