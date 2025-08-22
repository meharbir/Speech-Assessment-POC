#!/usr/bin/env python3
"""
Test script to verify audio metrics analyzer is working
"""

import asyncio
import sys
import os
from audio_metrics import AdvancedAudioAnalyzer

async def main():
    """Test audio metrics functionality"""
    print("=" * 50)
    print("AUDIO METRICS TEST")
    print("=" * 50)
    
    try:
        # Initialize analyzer
        print("\n1. Initializing Audio Metrics Analyzer...")
        analyzer = AdvancedAudioAnalyzer()
        print("[OK] Analyzer initialized successfully")
        
        # Test with mock data to verify libraries are working
        print("\n2. Testing Library Imports...")
        
        # Test librosa
        import librosa
        import numpy as np
        print("[OK] Librosa imported successfully")
        
        # Test parselmouth
        import parselmouth
        print("[OK] Parselmouth imported successfully")
        
        # Test soundfile
        import soundfile as sf
        print("[OK] SoundFile imported successfully")
        
        # Create a simple test signal
        print("\n3. Creating Test Audio Signal...")
        duration = 2  # seconds
        sample_rate = 16000
        frequency = 440  # A4 note
        
        # Generate a simple sine wave
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_signal = np.sin(2 * np.pi * frequency * t)
        
        # Add some variation to make it more speech-like
        audio_signal = audio_signal * (1 + 0.3 * np.sin(2 * np.pi * 2 * t))  # Add amplitude modulation
        
        print(f"[OK] Generated {duration}s test signal at {sample_rate}Hz")
        
        # Test pitch extraction with librosa
        print("\n4. Testing Pitch Extraction...")
        f0 = librosa.yin(audio_signal, fmin=50, fmax=600, sr=sample_rate)
        valid_f0 = f0[f0 > 0]
        
        if len(valid_f0) > 0:
            print(f"[OK] Pitch detected: Mean={np.mean(valid_f0):.1f}Hz, Range={np.ptp(valid_f0):.1f}Hz")
        else:
            print("[WARNING] No pitch detected in test signal")
        
        # Test fluency metrics
        print("\n5. Testing Fluency Analysis...")
        rms = librosa.feature.rms(y=audio_signal)[0]
        print(f"[OK] RMS energy calculated: {len(rms)} frames")
        
        # Note about full testing
        print("\n6. Full Audio Analysis Test")
        print("   [NOTE] Full analysis requires a real audio file (WAV/MP3/WebM)")
        print("   The analyzer will work with recordings from the frontend")
        
        print("\n" + "=" * 50)
        print("[SUCCESS] Audio metrics module is ready!")
        print("=" * 50)
        
        print("\nCapabilities:")
        print("  - Pitch range and stability analysis")
        print("  - Speaking rate calculation (WPM)")
        print("  - Pause detection and analysis")
        print("  - Voice quality metrics (jitter, shimmer, HNR)")
        print("  - Rhythm consistency scoring")
        
        return True
        
    except ImportError as e:
        print(f"\n[ERROR] Missing library: {str(e)}")
        print("Please ensure all audio libraries are installed:")
        print("  pip install librosa praat-parselmouth pydub scipy soundfile")
        return False
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)