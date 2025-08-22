"""
Advanced Audio Metrics Analysis Module
Based on the assessment framework for pronunciation and fluency evaluation
"""

import numpy as np
import librosa
import parselmouth
from parselmouth import praat
import soundfile as sf
import io
import logging
from typing import Dict, Any, Optional, Tuple
import tempfile
import os

logger = logging.getLogger(__name__)

class AdvancedAudioAnalyzer:
    """
    Analyzes audio for advanced metrics including:
    - Pitch range and stability
    - Speaking rate (WPM)
    - Pause analysis
    - Voice quality metrics (jitter, shimmer, HNR)
    - Rhythm consistency
    """
    
    # Assessment framework thresholds
    OPTIMAL_PITCH_RANGE = (85, 255)  # Hz
    MONOTONY_THRESHOLD = 30  # Hz standard deviation
    OPTIMAL_SPEAKING_RATE = (120, 160)  # WPM
    PROBLEMATIC_PAUSE_DURATION = 1.5  # seconds
    
    def __init__(self):
        """Initialize the audio analyzer"""
        logger.info("Advanced Audio Analyzer initialized")
    
    async def analyze_comprehensive_metrics(self, audio_data: bytes, transcript: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform comprehensive audio analysis
        
        Args:
            audio_data: Audio file data in bytes
            transcript: Optional transcript for calculating speaking rate
            
        Returns:
            Dictionary containing all audio metrics
        """
        try:
            logger.info("Starting comprehensive audio analysis")
            
            # Save audio data to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(audio_data)
            
            try:
                # Load audio with librosa
                audio_array, sample_rate = librosa.load(temp_path, sr=None)
                
                # Normalize audio
                if np.max(np.abs(audio_array)) > 0:
                    audio_array = audio_array / np.max(np.abs(audio_array))
                
                # Perform analyses
                pronunciation_metrics = self._analyze_pronunciation(audio_array, sample_rate)
                fluency_metrics = self._analyze_fluency(audio_array, sample_rate, transcript)
                voice_quality = self._analyze_voice_quality(temp_path)
                
                # Calculate overall assessments
                assessments = self._calculate_assessments(
                    pronunciation_metrics, 
                    fluency_metrics, 
                    voice_quality
                )
                
                # Combine all metrics
                result = {
                    "pronunciation_analysis": pronunciation_metrics,
                    "fluency_metrics": fluency_metrics,
                    "voice_quality": voice_quality,
                    "assessments": assessments,
                    "audio_duration_seconds": len(audio_array) / sample_rate
                }
                
                logger.info("Audio analysis completed successfully")
                return result
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Audio analysis failed: {str(e)}")
            return self._get_fallback_metrics(str(e))
    
    def _analyze_pronunciation(self, audio_array: np.ndarray, sr: int) -> Dict[str, Any]:
        """
        Analyze pronunciation-related metrics
        
        Includes:
        - Pitch range (85-255 Hz optimal)
        - Pitch stability (std dev <30 Hz indicates monotony)
        - Articulation quality indicators
        """
        try:
            # Extract pitch using YIN algorithm
            f0 = librosa.yin(audio_array, fmin=50, fmax=400, sr=sr)
            
            # Filter out silence (f0 == 0)
            valid_f0 = f0[f0 > 0]
            
            if len(valid_f0) == 0:
                return {
                    "pitch_range_hz": 0,
                    "pitch_mean_hz": 0,
                    "pitch_std_hz": 0,
                    "is_optimal_range": False,
                    "is_monotonous": True,
                    "feedback": "No pitch detected - please speak more clearly"
                }
            
            pitch_range = np.ptp(valid_f0)  # Peak-to-peak range
            pitch_mean = np.mean(valid_f0)
            pitch_std = np.std(valid_f0)
            
            # Check against optimal thresholds
            is_optimal = self.OPTIMAL_PITCH_RANGE[0] <= pitch_range <= self.OPTIMAL_PITCH_RANGE[1]
            is_monotonous = pitch_std < self.MONOTONY_THRESHOLD
            
            # Generate feedback
            feedback = self._generate_pitch_feedback(pitch_range, pitch_std, is_optimal, is_monotonous)
            
            return {
                "pitch_range_hz": float(pitch_range),
                "pitch_mean_hz": float(pitch_mean),
                "pitch_std_hz": float(pitch_std),
                "is_optimal_range": is_optimal,
                "is_monotonous": is_monotonous,
                "feedback": feedback,
                "pitch_contour_samples": valid_f0[:100].tolist() if len(valid_f0) > 100 else valid_f0.tolist()
            }
            
        except Exception as e:
            logger.error(f"Pronunciation analysis failed: {str(e)}")
            return {
                "pitch_range_hz": 0,
                "error": str(e)
            }
    
    def _analyze_fluency(self, audio_array: np.ndarray, sr: int, transcript: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze fluency-related metrics
        
        Includes:
        - Speaking rate (120-160 WPM optimal)
        - Pause frequency and duration
        - Rhythm consistency
        """
        try:
            # Detect pauses using energy-based approach
            hop_length = 512
            frame_length = 2048
            
            # Calculate RMS energy
            rms = librosa.feature.rms(y=audio_array, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Threshold for silence detection (adaptive)
            silence_threshold = np.percentile(rms, 20)
            
            # Find silent frames
            silent_frames = rms < silence_threshold
            
            # Convert frames to time
            frame_time = hop_length / sr
            
            # Find pause segments
            pauses = []
            pause_start = None
            
            for i, is_silent in enumerate(silent_frames):
                if is_silent and pause_start is None:
                    pause_start = i * frame_time
                elif not is_silent and pause_start is not None:
                    pause_duration = (i * frame_time) - pause_start
                    if pause_duration > 0.1:  # Only count pauses > 100ms
                        pauses.append(pause_duration)
                    pause_start = None
            
            # Calculate pause metrics
            total_pauses = len(pauses)
            long_pauses = sum(1 for p in pauses if p > self.PROBLEMATIC_PAUSE_DURATION)
            avg_pause_duration = np.mean(pauses) if pauses else 0
            
            # Calculate speaking rate if transcript is provided
            speaking_rate_wpm = None
            is_optimal_rate = None
            
            if transcript:
                word_count = len(transcript.split())
                duration_minutes = len(audio_array) / sr / 60
                speaking_duration_minutes = duration_minutes - (sum(pauses) / 60)
                
                if speaking_duration_minutes > 0:
                    speaking_rate_wpm = word_count / speaking_duration_minutes
                    is_optimal_rate = self.OPTIMAL_SPEAKING_RATE[0] <= speaking_rate_wpm <= self.OPTIMAL_SPEAKING_RATE[1]
            
            # Calculate rhythm consistency (variance in inter-pause intervals)
            rhythm_score = 100
            if len(pauses) > 1:
                inter_pause_intervals = np.diff([p for p in pauses])
                if len(inter_pause_intervals) > 0:
                    rhythm_variance = np.var(inter_pause_intervals)
                    # Lower variance = more consistent rhythm
                    rhythm_score = max(0, 100 - (rhythm_variance * 10))
            
            # Generate feedback
            feedback = self._generate_fluency_feedback(
                speaking_rate_wpm, 
                total_pauses, 
                long_pauses,
                is_optimal_rate
            )
            
            return {
                "speaking_rate_wpm": float(speaking_rate_wpm) if speaking_rate_wpm else None,
                "is_optimal_rate": is_optimal_rate,
                "total_pauses": total_pauses,
                "long_pauses": long_pauses,
                "avg_pause_duration_sec": float(avg_pause_duration),
                "rhythm_consistency_score": float(rhythm_score),
                "feedback": feedback
            }
            
        except Exception as e:
            logger.error(f"Fluency analysis failed: {str(e)}")
            return {
                "error": str(e)
            }
    
    def _analyze_voice_quality(self, audio_path: str) -> Dict[str, Any]:
        """
        Analyze voice quality metrics using Praat/Parselmouth
        
        Includes:
        - Jitter (local) - voice stability
        - Shimmer (local) - amplitude variation
        - Harmonics-to-Noise Ratio (HNR) - voice clarity
        """
        try:
            # Load audio with parselmouth
            sound = parselmouth.Sound(audio_path)
            
            # Extract voice quality metrics
            # Jitter (normal < 1.04%)
            jitter = praat.call(sound, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
            jitter_percent = jitter * 100
            
            # Shimmer (normal < 3.81%)
            shimmer = praat.call(sound, "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
            shimmer_percent = shimmer * 100
            
            # HNR (good > 20 dB)
            hnr_values = praat.call(sound, "To Harmonicity (cc)", 0.01, 75, 0.1, 1.0)
            hnr_mean = praat.call(hnr_values, "Get mean", 0, 0)
            
            # Assess voice quality
            is_jitter_normal = jitter_percent < 1.04
            is_shimmer_normal = shimmer_percent < 3.81
            is_hnr_good = hnr_mean > 20
            
            # Generate feedback
            feedback = self._generate_voice_quality_feedback(
                jitter_percent,
                shimmer_percent,
                hnr_mean,
                is_jitter_normal,
                is_shimmer_normal,
                is_hnr_good
            )
            
            return {
                "jitter_percent": float(jitter_percent),
                "shimmer_percent": float(shimmer_percent),
                "hnr_db": float(hnr_mean),
                "is_jitter_normal": is_jitter_normal,
                "is_shimmer_normal": is_shimmer_normal,
                "is_hnr_good": is_hnr_good,
                "feedback": feedback
            }
            
        except Exception as e:
            logger.error(f"Voice quality analysis failed: {str(e)}")
            return {
                "error": str(e)
            }
    
    def _calculate_assessments(self, pronunciation: Dict, fluency: Dict, voice_quality: Dict) -> Dict[str, Any]:
        """Calculate overall assessments based on all metrics"""
        
        # Pronunciation score
        pronunciation_score = 100
        if pronunciation.get("is_monotonous"):
            pronunciation_score -= 20
        if not pronunciation.get("is_optimal_range"):
            pronunciation_score -= 15
        
        # Fluency score
        fluency_score = 100
        if fluency.get("long_pauses", 0) > 0:
            fluency_score -= (fluency["long_pauses"] * 10)
        if fluency.get("is_optimal_rate") == False:
            fluency_score -= 15
        fluency_score = max(0, fluency_score)
        
        # Voice quality score
        voice_score = 100
        if not voice_quality.get("is_jitter_normal", True):
            voice_score -= 10
        if not voice_quality.get("is_shimmer_normal", True):
            voice_score -= 10
        if not voice_quality.get("is_hnr_good", True):
            voice_score -= 15
        
        # Overall score
        overall_score = (pronunciation_score + fluency_score + voice_score) / 3
        
        return {
            "pronunciation_score": pronunciation_score,
            "fluency_score": fluency_score,
            "voice_quality_score": voice_score,
            "overall_audio_score": overall_score,
            "summary": self._generate_overall_summary(pronunciation_score, fluency_score, voice_score)
        }
    
    def _generate_pitch_feedback(self, pitch_range: float, pitch_std: float, 
                                 is_optimal: bool, is_monotonous: bool) -> str:
        """Generate human-readable feedback for pitch metrics"""
        feedback_parts = []
        
        if is_optimal:
            feedback_parts.append("Good pitch variation showing expressiveness")
        else:
            if pitch_range < self.OPTIMAL_PITCH_RANGE[0]:
                feedback_parts.append("Try to vary your pitch more for better expressiveness")
            else:
                feedback_parts.append("Pitch variation is too extreme, try to moderate it")
        
        if is_monotonous:
            feedback_parts.append("Speech sounds monotonous - add more emotion and emphasis")
        
        return ". ".join(feedback_parts) if feedback_parts else "Pitch characteristics are good"
    
    def _generate_fluency_feedback(self, wpm: Optional[float], total_pauses: int, 
                                   long_pauses: int, is_optimal: Optional[bool]) -> str:
        """Generate human-readable feedback for fluency metrics"""
        feedback_parts = []
        
        if wpm and is_optimal is not None:
            if is_optimal:
                feedback_parts.append(f"Good speaking pace at {wpm:.0f} words per minute")
            elif wpm < self.OPTIMAL_SPEAKING_RATE[0]:
                feedback_parts.append(f"Speaking too slowly ({wpm:.0f} WPM) - try to speak more naturally")
            else:
                feedback_parts.append(f"Speaking too fast ({wpm:.0f} WPM) - slow down for clarity")
        
        if long_pauses > 0:
            feedback_parts.append(f"Detected {long_pauses} long pause(s) - try to maintain flow")
        
        return ". ".join(feedback_parts) if feedback_parts else "Fluency is good"
    
    def _generate_voice_quality_feedback(self, jitter: float, shimmer: float, hnr: float,
                                         is_jitter_normal: bool, is_shimmer_normal: bool,
                                         is_hnr_good: bool) -> str:
        """Generate human-readable feedback for voice quality"""
        feedback_parts = []
        
        if not is_jitter_normal:
            feedback_parts.append("Voice stability could be improved - try to maintain steady tone")
        
        if not is_shimmer_normal:
            feedback_parts.append("Volume consistency needs work - maintain steady volume")
        
        if not is_hnr_good:
            feedback_parts.append("Voice clarity could be better - speak more clearly")
        
        if is_jitter_normal and is_shimmer_normal and is_hnr_good:
            feedback_parts.append("Excellent voice quality with good clarity and stability")
        
        return ". ".join(feedback_parts)
    
    def _generate_overall_summary(self, pronunciation_score: float, 
                                  fluency_score: float, voice_score: float) -> str:
        """Generate overall summary feedback"""
        avg_score = (pronunciation_score + fluency_score + voice_score) / 3
        
        if avg_score >= 85:
            return "Excellent overall speech quality! Keep up the great work."
        elif avg_score >= 70:
            return "Good speech quality with room for improvement in specific areas."
        elif avg_score >= 55:
            return "Fair speech quality - focus on the areas highlighted for improvement."
        else:
            return "Needs significant improvement - practice regularly and focus on feedback."
    
    def _get_fallback_metrics(self, error_msg: str) -> Dict[str, Any]:
        """Return fallback metrics when analysis fails"""
        return {
            "error": error_msg,
            "pronunciation_analysis": {
                "error": "Analysis unavailable"
            },
            "fluency_metrics": {
                "error": "Analysis unavailable"
            },
            "voice_quality": {
                "error": "Analysis unavailable"
            },
            "assessments": {
                "pronunciation_score": 0,
                "fluency_score": 0,
                "voice_quality_score": 0,
                "overall_audio_score": 0,
                "summary": "Audio analysis failed - please try again"
            }
        }


# Test function for verification
async def test_audio_metrics():
    """Test the audio metrics analyzer with a sample audio file"""
    import os
    
    analyzer = AdvancedAudioAnalyzer()
    
    # Check if we have a test audio file
    test_file = "test_audio.wav"
    
    if not os.path.exists(test_file):
        print(f"[WARNING] No test audio file found at {test_file}")
        print("Audio metrics analyzer is ready but needs an audio file to test")
        return False
    
    try:
        # Read the test audio file
        with open(test_file, 'rb') as f:
            audio_data = f.read()
        
        # Test with a sample transcript
        sample_transcript = "This is a test of the audio analysis system"
        
        print("Testing audio metrics analyzer...")
        result = await analyzer.analyze_comprehensive_metrics(audio_data, sample_transcript)
        
        print("\nAnalysis Results:")
        print(f"Pronunciation Score: {result['assessments']['pronunciation_score']}/100")
        print(f"Fluency Score: {result['assessments']['fluency_score']}/100")
        print(f"Voice Quality Score: {result['assessments']['voice_quality_score']}/100")
        print(f"Overall Score: {result['assessments']['overall_audio_score']:.1f}/100")
        
        if 'pronunciation_analysis' in result:
            print(f"\nPitch Range: {result['pronunciation_analysis'].get('pitch_range_hz', 'N/A')} Hz")
            print(f"Is Monotonous: {result['pronunciation_analysis'].get('is_monotonous', 'N/A')}")
        
        if 'fluency_metrics' in result:
            print(f"\nSpeaking Rate: {result['fluency_metrics'].get('speaking_rate_wpm', 'N/A')} WPM")
            print(f"Long Pauses: {result['fluency_metrics'].get('long_pauses', 'N/A')}")
        
        if 'voice_quality' in result:
            print(f"\nJitter: {result['voice_quality'].get('jitter_percent', 'N/A')}%")
            print(f"Shimmer: {result['voice_quality'].get('shimmer_percent', 'N/A')}%")
            print(f"HNR: {result['voice_quality'].get('hnr_db', 'N/A')} dB")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # For testing purposes
    import asyncio
    asyncio.run(test_audio_metrics())