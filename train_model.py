import librosa
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
import joblib

# Global Parameters (Shared with risk_scorer.py)
PROCESSED_PATH = 'processed_data/' 
TARGET_DURATION = 3.0 
N_MFCC = 40  # Number of MFCCs to extract
# Setting a high sample rate ensures quality but requires more memory
SAMPLE_RATE = 22050 

def extract_features(file_path, sample_rate=SAMPLE_RATE):
    """Loads audio, extracts various features (MFCCs, Chroma, Mel), and combines them."""
    try:
        # Load the 3.0s audio file with the defined sample rate
        audio, sr = librosa.load(file_path, sr=sample_rate, duration=TARGET_DURATION)
        
        # 1. MFCCs (Mel-Frequency Cepstral Coefficients)
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=N_MFCC)
        mfccs_mean = np.mean(mfccs.T, axis=0)
        mfccs_stdev = np.std(mfccs.T, axis=0)
        
        # 2. Chroma (measures intensity of pitches)
        chroma = librosa.feature.chroma_stft(y=audio, sr=sr)
        chroma_mean = np.mean(chroma.T, axis=0)
        chroma_stdev = np.std(chroma.T, axis=0)

        # 3. Mel Spectrogram (representation of sound)
        mel = librosa.feature.melspectrogram(y=audio, sr=sr)
        mel_mean = np.mean(mel.T, axis=0)
        mel_stdev = np.std(mel.T, axis=0)
        
        # Combine all mean and standard deviation features into one vector
        feature_vector = np.hstack([
            mfccs_mean, mfccs_stdev, 
            chroma_mean, chroma_stdev, 
            mel_mean, mel_stdev
        ])
        
        return feature_vector
        
    except Exception as e:
        print(f"Error extracting features from {file_path}: {e}")
        return None

# Load all standardized data
features = []
labels = []

print("Extracting enhanced features (MFCCs, Chroma, Mel) from 3.0s audio clips...")
for filename in os.listdir(PROCESSED_PATH):
    if filename.endswith('.wav'):
        file_path = os.path.join(PROCESSED_PATH, filename)
        label = filename.split('_')[1] 

        feature = extract_features(file_path)

        if feature is not None:
            features.append(feature)
            labels.append(label)

X = np.array(features)
y = np.array(labels)

print(f"Total samples processed: {len(X)}")
print(f"Feature vector size: {X.shape[1]} (Increased for better performance)")

# 1. Split Data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 2. FEATURE SCALING
print("Scaling features...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 3. Train the Classifier
print("Training MLP Classifier on SCALED features...")
audio_model = MLPClassifier(
    alpha=0.01,
    batch_size=256,
    epsilon=1e-08,
    hidden_layer_sizes=(300, 300),
    learning_rate='adaptive',
    max_iter=1000, 
    random_state=42
)

# Fit the model to the SCALED training data
audio_model.fit(X_train_scaled, y_train)

# 4. Evaluate Performance
y_pred = audio_model.predict(X_test_scaled)
accuracy = accuracy_score(y_test, y_pred)
print(f"Model Training Complete. New Test Accuracy: {accuracy*100:.2f}%")

# 5. Save the Model AND the Scaler
MODEL_FILENAME = 'audio_distress_model.joblib'
SCALER_FILENAME = 'feature_scaler.joblib'

joblib.dump(audio_model, MODEL_FILENAME)
joblib.dump(scaler, SCALER_FILENAME)
print(f"Trained model saved as {MODEL_FILENAME}")
print(f"Feature scaler saved as {SCALER_FILENAME}")