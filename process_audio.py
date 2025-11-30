import librosa
import soundfile as sf
import os
import numpy as np

# Define the required duration in seconds
TARGET_DURATION = 3.0 

# Path to your TESS data (adjust if needed)
DATA_PATH = 'data/' 

# New folder for processed 3.0s files
PROCESSED_PATH = 'processed_data/' 
os.makedirs(PROCESSED_PATH, exist_ok=True)

print("Starting audio standardization...")

for root, dirs, files in os.walk(DATA_PATH):
    for file in files:
        if file.endswith('.wav'):
            file_path = os.path.join(root, file)

            # 1. Load the audio file
            # sr=None preserves the original sampling rate
            audio, sr = librosa.load(file_path, sr=None) 

            # Calculate the number of samples for the target duration
            target_samples = int(TARGET_DURATION * sr)

            if len(audio) > target_samples:
                # 2. Trim: Audio is too long, trim to target_samples
                audio_processed = audio[:target_samples]
            elif len(audio) < target_samples:
                # 3. Pad: Audio is too short, pad with zeros
                padding_length = target_samples - len(audio)
                audio_processed = np.pad(audio, (0, padding_length), 'constant')
            else:
                # 4. Correct length
                audio_processed = audio

            # 5. Save the standardized file to the new folder
            # The filename (which contains the emotion label) remains the same
            new_file_path = os.path.join(PROCESSED_PATH, file)
            sf.write(new_file_path, audio_processed, sr)

print("Audio standardization complete! Files saved to:", PROCESSED_PATH)