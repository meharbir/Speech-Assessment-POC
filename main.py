import os
import json
import uuid
import subprocess
import base64
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import io
import requests
from openai import OpenAI # The missing import
import azure.cognitiveservices.speech as speechsdk # Re-added for TTS

# --- Load Environment & Initialize App ---
load_dotenv()
app = FastAPI()

# --- CORS Configuration ---
origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Azure & FFmpeg Configuration ---
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FFMPEG_PATH = r"C:\ffmpeg\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"

# The Correct REST API Endpoint
PRONUNCIATION_ASSESSMENT_ENDPOINT = f"https://{AZURE_SPEECH_REGION}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language=en-US"

# --- Initialize AI Clients ---
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
else:
    openai_client = None

# Re-added for TTS
speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)

# --- Main API Endpoint ---
@app.post("/api/analyze")
async def analyze_speech(audio_file: UploadFile = File(...), reference_text: str = Form(...)):
    print(f"\n=== NEW REQUEST ===")
    print(f"Reference text: '{reference_text}'")
    print(f"Azure Key present: {bool(AZURE_SPEECH_KEY)}")
    print(f"Azure Region: {AZURE_SPEECH_REGION}")
    
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        raise HTTPException(status_code=500, detail="Azure credentials are not configured.")

    # STEP 1: Audio Conversion using a direct FFmpeg subprocess call
    try:
        print(f"Step 1: Reading audio file...")
        audio_bytes = await audio_file.read()
        print(f"Audio size: {len(audio_bytes)} bytes")
        
        print(f"Step 2: Converting with FFmpeg at {FFMPEG_PATH}...")
        ffmpeg_command = [ FFMPEG_PATH, '-i', 'pipe:0', '-ac', '1', '-ar', '16000', '-f', 'wav', 'pipe:1' ]
        process = subprocess.run(ffmpeg_command, input=audio_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        wav_data = process.stdout
        print(f"Converted WAV size: {len(wav_data)} bytes")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg ERROR: {e.stderr.decode()}")
        raise HTTPException(status_code=500, detail=f"FFmpeg failed to convert audio: {e.stderr.decode()}")
    except Exception as e:
        print(f"Audio processing ERROR: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to process audio file. Error: {e}")

    # STEP 2: Call the Correct Azure Pronunciation Assessment API
    try:
        print(f"\nStep 3: Calling Azure Speech API...")
        print(f"Endpoint: {PRONUNCIATION_ASSESSMENT_ENDPOINT}")
        
        pronunciation_assessment_params = { 
            "ReferenceText": reference_text, 
            "GradingSystem": "HundredMark", 
            "Granularity": "Phoneme", 
            "EnableMiscue": "True"  # Changed from boolean to string!
        }
        
        # Azure requires the pronunciation assessment params to be base64 encoded
        pronunciation_assessment_json = json.dumps(pronunciation_assessment_params)
        pronunciation_assessment_base64 = base64.b64encode(pronunciation_assessment_json.encode('utf-8')).decode('utf-8')
        
        headers = {
            'Content-Type': 'audio/wav; codecs=audio/pcm; samplerate=16000',
            'Ocp-Apim-Subscription-Key': AZURE_SPEECH_KEY,
            'Pronunciation-Assessment': pronunciation_assessment_base64,  # Base64 encoded!
            'Accept': 'application/json;text/xml'
        }
        
        print(f"Pronunciation params (raw): {pronunciation_assessment_json}")
        print(f"Pronunciation params (base64): {pronunciation_assessment_base64}")
        print(f"Headers: {dict(headers)}")
        print(f"Making request...")
        
        response = requests.post(url=PRONUNCIATION_ASSESSMENT_ENDPOINT, headers=headers, data=wav_data)
        
        print(f"Azure response status: {response.status_code}")
        print(f"Azure response headers: {dict(response.headers)}")
        
        # CRITICAL: Read the response body BEFORE raise_for_status()
        if response.status_code != 200:
            print(f"Azure error response body: {response.text}")
            print(f"Azure error response (as JSON if possible): {response.json() if response.headers.get('content-type', '').startswith('application/json') else 'Not JSON'}")
        
        response.raise_for_status()
        assessment_data = response.json()
        
        print(f"Azure response data: {json.dumps(assessment_data, indent=2)}")
        
        # Placeholder for LLM logic
        logical_flow_result = { "coherence_feedback": "LLM analysis will be integrated next.", "rephrasing_suggestions": [], "ending_recommendation": "" }
        
        final_response = { "azureAssessment": assessment_data.get("NBest")[0], "logicalFlowAnalysis": logical_flow_result }
        return JSONResponse(content=final_response)

    except requests.exceptions.RequestException as e:
        print(f"\nAzure API ERROR:")
        print(f"Status Code: {e.response.status_code if e.response else 'No response'}")
        print(f"Response Body: {e.response.text if e.response else 'No response body'}")
        print(f"Response Headers: {dict(e.response.headers) if e.response else 'No headers'}")
        
        error_detail = f"Error communicating with Azure. Status: {e.response.status_code if e.response else 'N/A'}. Body: {e.response.text if e.response else 'No response'}"
        raise HTTPException(status_code=502, detail=error_detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during analysis: {e}")

# --- Re-added Text-to-Speech Endpoint ---
@app.get("/api/synthesize")
async def synthesize_speech(word: str):
    if not word:
        raise HTTPException(status_code=400, detail="No word provided.")
    
    # Fix for TTS - don't specify audio config, let it use defaults
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
    result = synthesizer.speak_text_async(word).get()
    
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return StreamingResponse(io.BytesIO(result.audio_data), media_type="audio/wav")
    else:
        cancellation_details = result.cancellation_details
        raise HTTPException(status_code=500, detail=f"TTS Canceled: {cancellation_details.reason}")