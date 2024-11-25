import os
import numpy as np
import librosa
import librosa.display
import matplotlib.pyplot as plt
import random
import soundfile as sf
from sklearn.model_selection import train_test_split
from sklearn.mixture import GaussianMixture
from sklearn.metrics import accuracy_score, confusion_matrix
import logging

# Set up logging
logging.basicConfig(filename='voice_auth_research.log', level=logging.INFO, format='%(asctime)s %(message)s')

# Voice dataset directory
VOICE_SAMPLES_PATH = 'voice_samples/'

# Function to extract MFCC features from audio files
def extract_features(file_path, n_mfcc=13):
    logging.info(f"Extracting features from: {file_path}")
    try:
        audio, sample_rate = librosa.load(file_path, sr=None)
        mfcc = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=n_mfcc)
        mfcc_mean = np.mean(mfcc, axis=1)
        return mfcc_mean
    except Exception as e:
        logging.error(f"Error extracting features: {e}")
        return None

# Prepare dataset of voice samples
def prepare_dataset(voice_samples_path):
    X = []
    y = []
    speakers = os.listdir(voice_samples_path)
    for speaker in speakers:
        speaker_folder = os.path.join(voice_samples_path, speaker)
        if os.path.isdir(speaker_folder):
            for file_name in os.listdir(speaker_folder):
                file_path = os.path.join(speaker_folder, file_name)
                if file_name.endswith('.wav'):
                    features = extract_features(file_path)
                    if features is not None:
                        X.append(features)
                        y.append(speaker)
    return np.array(X), np.array(y)

# Train GMM model for voice authentication
def train_gmm_model(X_train, y_train):
    models = {}
    unique_speakers = np.unique(y_train)
    for speaker in unique_speakers:
        logging.info(f"Training GMM for speaker: {speaker}")
        speaker_data = X_train[y_train == speaker]
        gmm = GaussianMixture(n_components=8, covariance_type='diag', max_iter=200, random_state=42)
        gmm.fit(speaker_data)
        models[speaker] = gmm
    return models

# Test voice samples against trained models
def test_gmm_models(models, X_test, y_test):
    y_pred = []
    for sample in X_test:
        scores = {speaker: model.score(sample.reshape(1, -1)) for speaker, model in models.items()}
        predicted_speaker = max(scores, key=scores.get)
        y_pred.append(predicted_speaker)
    return y_pred

# Method to generate voice sample variations for bypass testing
def generate_bypass_samples(original_sample_path, output_path):
    try:
        audio, sample_rate = librosa.load(original_sample_path, sr=None)
        # Create pitch-shifted version
        pitch_shifted = librosa.effects.pitch_shift(audio, sample_rate, n_steps=random.uniform(-2, 2))
        sf.write(os.path.join(output_path, 'pitch_shifted.wav'), pitch_shifted, sample_rate)
        # Create time-stretched version
        time_stretched = librosa.effects.time_stretch(audio, rate=random.uniform(0.8, 1.2))
        sf.write(os.path.join(output_path, 'time_stretched.wav'), time_stretched, sample_rate)
        logging.info(f"Generated bypass samples for {original_sample_path}")
    except Exception as e:
        logging.error(f"Error generating bypass samples: {e}")

if __name__ == "__main__":
    # Prepare dataset for training and testing
    if not os.path.exists(VOICE_SAMPLES_PATH):
        logging.error("Voice samples path not found.")
        exit("Error: Voice samples directory does not exist.")

    X, y = prepare_dataset(VOICE_SAMPLES_PATH)
    if len(X) == 0:
        logging.error("No valid voice samples found.")
        exit("Error: No valid voice samples found.")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train GMM models for each speaker
    gmm_models = train_gmm_model(X_train, y_train)
    logging.info("Model training complete.")

    # Test GMM models
    y_pred = test_gmm_models(gmm_models, X_test, y_test)
    accuracy = accuracy_score(y_test, y_pred)
    logging.info(f"Test accuracy: {accuracy:.2f}")
    conf_matrix = confusion_matrix(y_test, y_pred)
    logging.info(f"Confusion Matrix:\n{conf_matrix}")

    # Generate bypass samples for testing
    for speaker in os.listdir(VOICE_SAMPLES_PATH):
        speaker_folder = os.path.join(VOICE_SAMPLES_PATH, speaker)
        if os.path.isdir(speaker_folder):
            original_sample = os.path.join(speaker_folder, os.listdir(speaker_folder)[0])
            generate_bypass_samples(original_sample, speaker_folder)
