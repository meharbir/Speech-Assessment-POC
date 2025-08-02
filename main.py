import os
import json
import uuid
import subprocess
import io
import base64
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import OpenAI
import azure.cognitiveservices.speech as speechsdk

# --- CONFIGURATION & INITIALIZATION ---
load_dotenv()
app = FastAPI()

origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FFMPEG_PATH = r"C:\ffmpeg\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)

# --- HELPER FUNCTIONS ---

def convert_audio_with_ffmpeg(audio_bytes: bytes) -> bytes:
    try:
        ffmpeg_command = [FFMPEG_PATH, '-i', 'pipe:0', '-ac', '1', '-ar', '16000', '-f', 'wav', 'pipe:1']
        process = subprocess.run(ffmpeg_command, input=audio_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return process.stdout
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg failed: {e.stderr.decode()}")

def get_pronunciation_assessment(wav_data: bytes, reference_text: str) -> dict:
    endpoint = f"https://{AZURE_SPEECH_REGION}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language=en-US"
    params = {"ReferenceText": reference_text, "GradingSystem": "HundredMark", "Granularity": "Phoneme", "EnableMiscue": "True"}
    params_json = json.dumps(params)
    params_base64 = base64.b64encode(params_json.encode('utf-8')).decode('utf-8')
    headers = {'Content-Type': 'audio/wav; codecs=audio/pcm; samplerate=16000', 'Ocp-Apim-Subscription-Key': AZURE_SPEECH_KEY, 'Pronunciation-Assessment': params_base64, 'Accept': 'application/json;text/xml'}
    try:
        response = requests.post(url=endpoint, headers=headers, data=wav_data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Azure Pronunciation API Error: {e.response.text if e.response else str(e)}")

def get_stt_result(wav_data: bytes) -> dict:
    endpoint = f"https://{AZURE_SPEECH_REGION}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language=en-US&format=detailed"
    headers = {'Content-Type': 'audio/wav', 'Ocp-Apim-Subscription-Key': AZURE_SPEECH_KEY, 'Accept': 'application/json'}
    try:
        response = requests.post(url=endpoint, headers=headers, data=wav_data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Azure STT API Error: {e.response.text if e.response else str(e)}")
        
def get_ai_coach_feedback(transcript: str, topic: str, duration_seconds: float, word_count: int) -> dict:
    if not openai_client: 
        return {"error": "OpenAI client not configured."}
    
    words_per_minute = (word_count / duration_seconds) * 60 if duration_seconds > 0 else 0

    # --- NEW, HIGHLY-DETAILED "SENIOR ENGLISH TUTOR" PROMPT ---
    prompt = f"""
    You are an expert, encouraging, and insightful Senior English Tutor evaluating a 4th-grade student's impromptu speech.
    The student's task was to speak for 1-2 minutes on the topic: "{topic}".
    Their speech was {duration_seconds:.1f} seconds long with a pace of {words_per_minute:.0f} words per minute.
    The transcript of their speech is: "{transcript}"

    Your task is to provide a detailed, personalized, and actionable evaluation. Your response MUST be a valid JSON object.
    You MUST provide a value for every key. If there are no grammar errors, provide an empty array for "grammar_errors".

    Scoring Guidelines (0-100):
    - 0-40: Beginner (many errors, needs significant improvement)
    - 41-70: Intermediate (some errors, generally understandable)
    - 71-90: Advanced (minor errors, clear and effective communication)
    - 91-100: Proficient (excellent, near-native level)

    Here is the required JSON structure. Follow it with 100% accuracy:
    {{
        "fluency_score": <integer: Score based on pace and rhythm. Target for a 4th grader is ~110-140 WPM>,
        "fluency_feedback": "<string: A personalized comment on their speaking pace and rhythm.>",
        "grammar_score": <integer: Score based on the number and severity of errors>,
        "grammar_errors": [
            {{"error": "<string: The exact phrase with the error>", "correction": "<string: The corrected phrase>", "explanation": "<string: A simple, encouraging explanation of the grammar rule>"}}
        ],
        "vocabulary_score": <integer: Score based on word choice variety and appropriateness>,
        "vocabulary_feedback": "<string: A personalized comment on their word choice. Suggest 1-2 more descriptive words they could have used.>",
        "coherence_score": <integer: Score based on how logical and easy to follow the speech is>,
        "coherence_feedback": "<string: A personalized comment on the structure and flow of their ideas.>",
        "positive_highlights": [
            "<string: A specific, positive, and encouraging comment about something they did well.>"
        ],
        "rewritten_sample": "<string: Rewrite their speech into a short, improved paragraph (2-3 sentences) that demonstrates better grammar, vocabulary, and structure. This is a model answer for them to learn from.>"
    }}
    """
    try:
        response = openai_client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": prompt}], response_format={"type": "json_object"})
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API Error: {str(e)}")

# --- API ENDPOINTS ---
@app.post("/api/analyze")
async def analyze_speech(mode: str = Query(...), audio_file: UploadFile = File(...), reference_text: str = Form(None), topic: str = Form(None)):
    audio_bytes = await audio_file.read()
    wav_data = convert_audio_with_ffmpeg(audio_bytes)
    if mode == 'pronunciation':
        if not reference_text: raise HTTPException(status_code=400, detail="Reference text required.")
        azure_data = get_pronunciation_assessment(wav_data, reference_text)
        return JSONResponse(content={"mode": "pronunciation", "azureAssessment": azure_data.get("NBest")[0]})
    elif mode == 'impromptu':
        if not topic: raise HTTPException(status_code=400, detail="Topic is required.")
        stt_result = get_stt_result(wav_data)
        transcript = stt_result.get("DisplayText", "")
        if not transcript: raise HTTPException(status_code=400, detail="Could not detect speech.")
        nbest = stt_result.get("NBest", [{}])[0]
        duration_seconds = nbest.get("Duration", 0) / 10000000.0
        word_count = len(nbest.get("Words", []))
        ai_coach_analysis = get_ai_coach_feedback(transcript, topic, duration_seconds, word_count)
        final_result = { "mode": "impromptu", "transcript": transcript, "azureMetrics": { "wordCount": word_count, "duration": duration_seconds }, "aiCoachAnalysis": ai_coach_analysis }
        return JSONResponse(content=final_result)
    else:
        raise HTTPException(status_code=400, detail="Invalid analysis mode specified.")

# UPDATED Text-to-Speech Endpoint for single words
@app.get("/api/synthesize")
async def synthesize_speech(word: str):
    if not word: raise HTTPException(status_code=400, detail="No word provided.")
    
    # Set the desired Indian English voice
    speech_config.speech_synthesis_voice_name = "en-IN-NeerjaNeural"
    
    # Use default audio output configuration for streaming
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    result = synthesizer.speak_text_async(word).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return StreamingResponse(io.BytesIO(result.audio_data), media_type="audio/wav")
    else:
        raise HTTPException(status_code=500, detail=f"TTS Canceled: {result.cancellation_details.reason}")

# NEW Pydantic model for the paragraph request body
class TextToSynthesize(BaseModel):
    text: str

# NEW Text-to-Speech Endpoint for paragraphs
@app.post("/api/synthesize-paragraph")
async def synthesize_paragraph(item: TextToSynthesize):
    if not item.text:
        raise HTTPException(status_code=400, detail="No text provided.")
    
    # Set the desired Indian English voice
    speech_config.speech_synthesis_voice_name = "en-IN-NeerjaNeural"
    
    # Use default audio output configuration for streaming
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    result = synthesizer.speak_text_async(item.text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return StreamingResponse(io.BytesIO(result.audio_data), media_type="audio/wav")
    else:
        raise HTTPException(status_code=500, detail=f"TTS Canceled: {result.cancellation_details.reason}")

# --- Static Files ---
app.mount("/", StaticFiles(directory="static", html=True), name="static")