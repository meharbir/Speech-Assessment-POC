from pydub import AudioSegment

print("Attempting to configure FFmpeg...")

try:
    # Use the exact same path as in your main.py
    AudioSegment.converter = r"C:\ffmpeg\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"
    print("✅ Success! Pydub and FFmpeg are configured correctly.")
except Exception as e:
    print(f"❌ Error: Could not configure Pydub. {e}")
    