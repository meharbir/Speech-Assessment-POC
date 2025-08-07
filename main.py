import os
import json
import uuid
import subprocess
import io
import base64
import requests
import math
import tempfile
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import OpenAI
import azure.cognitiveservices.speech as speechsdk
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
from sqlmodel import create_engine, SQLModel

# --- NEW IMPORTS FOR AUTH ---
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, create_engine, select, SQLModel
from typing import Annotated
from datetime import datetime, timedelta, timezone
# --- END NEW IMPORTS ---

from models import User, Session as DBSession, Topic # Renamed to avoid conflict

# --- CONFIGURATION & INITIALIZATION ---
load_dotenv()
app = FastAPI()

# --- DATABASE CONNECTION ---
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Connect to the database and create tables on startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# --- SECURITY CONFIGURATION ---
SECRET_KEY = os.getenv("SECRET_KEY", "a_super_secret_dev_key_change_this") # CHANGE IN PRODUCTION
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- HELPER & DEPENDENCY FUNCTIONS ---
def get_session():
    with Session(engine) as session:
        yield session

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- FEATURE FLAGS ---
ENABLE_TEXT_CORRECTION = False  # Set to True to enable GPT-4 text correction for pronunciation assessment

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
FFPROBE_PATH = r"C:\ffmpeg\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe"
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")

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
    params = {
        "ReferenceText": reference_text, 
        "GradingSystem": "HundredMark", 
        "Granularity": "Phoneme", 
        "EnableMiscue": "True"
    }
    params_json = json.dumps(params)
    params_base64 = base64.b64encode(params_json.encode('utf-8')).decode('utf-8')
    headers = {'Content-Type': 'audio/wav; codecs=audio/pcm; samplerate=16000', 'Ocp-Apim-Subscription-Key': AZURE_SPEECH_KEY, 'Pronunciation-Assessment': params_base64, 'Accept': 'application/json;text/xml'}
    
    # DETAILED DEBUG LOGGING BEFORE API CALL
    print(f"\n{'='*60}")
    print(f"AZURE PRONUNCIATION API DEBUG")
    print(f"{'='*60}")
    print(f"Audio data size: {len(wav_data)} bytes")
    print(f"Reference text length: {len(reference_text)} characters")
    print(f"Reference text preview: '{reference_text[:100]}{'...' if len(reference_text) > 100 else ''}'")
    print(f"Word count in reference: {len(reference_text.split())}")
    print(f"Endpoint: {endpoint}")
    print(f"Params JSON: {params_json}")
    print(f"Params Base64 length: {len(params_base64)}")
    print(f"Headers: {dict(headers)}")
    print(f"{'='*60}\n")
    
    try:
        response = requests.post(url=endpoint, headers=headers, data=wav_data)
        
        # LOG RESPONSE DETAILS BEFORE CHECKING STATUS
        print(f"\n{'*'*60}")
        print(f"AZURE PRONUNCIATION API RESPONSE")
        print(f"{'*'*60}")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text[:500]}{'...' if len(response.text) > 500 else ''}")
        print(f"{'*'*60}\n")
        
        response.raise_for_status()
        result = response.json()
        
        # Debug: Print what Azure actually returns
        if result.get("NBest") and len(result["NBest"]) > 0:
            nbest = result["NBest"][0]
            print(f"Azure Pronunciation Scores Received:")
            print(f"  - PronunciationScore: {nbest.get('PronunciationScore', 'NOT FOUND')}")
            print(f"  - AccuracyScore: {nbest.get('AccuracyScore', 'NOT FOUND')}")
            print(f"  - FluencyScore: {nbest.get('FluencyScore', 'NOT FOUND')}")
            print(f"  - ProsodyScore: {nbest.get('ProsodyScore', 'NOT FOUND')}")
            print(f"  - CompletenessScore: {nbest.get('CompletenessScore', 'NOT FOUND')}")
        
        return result
    except requests.exceptions.RequestException as e:
        # ENHANCED ERROR LOGGING
        print(f"\n{'!'*60}")
        print(f"AZURE PRONUNCIATION API ERROR")
        print(f"{'!'*60}")
        print(f"Status Code: {e.response.status_code if e.response else 'No response'}")
        print(f"Error Response Body: {e.response.text if e.response else 'No response body'}")
        print(f"Exception: {str(e)}")
        print(f"{'!'*60}\n")
        
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
        
# --- NEW ASYNC HELPER FOR A SINGLE CHUNK ---
async def process_chunk_async(chunk_data: bytes) -> dict:
    """Asynchronously calls the STT API for a single chunk of audio."""
    # In a real-world scenario with high traffic, you might use an async HTTP client like httpx.
    # For our MVP, running the synchronous `requests` call in an async executor is a robust solution.
    loop = asyncio.get_event_loop()
    stt_result = await loop.run_in_executor(None, get_stt_result, chunk_data)
    return stt_result

def generate_dynamic_reference_text(wav_data: bytes) -> str:
    """
    Takes audio, gets a raw transcript from Azure STT,
    and then uses an LLM to correct it into a clean reference text.
    """
    print("Step A: Getting raw transcript from Azure STT...")
    stt_result = get_stt_result(wav_data)
    raw_transcript = stt_result.get("DisplayText", "")
    
    if not raw_transcript:
        raise HTTPException(status_code=400, detail="Could not detect speech for initial transcription.")
    
    print(f"Step B: Got raw transcript: '{raw_transcript}'")
    print("Step C: Sending to LLM for correction...")

    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI client not configured for correction.")

    correction_prompt = f"""
    You are an expert English editor. A student provided a speech transcript that may contain grammatical errors or misrecognized words. 
    Your task is to correct it into a clean, grammatically perfect, and logical sentence or paragraph.
    The raw transcript is: "{raw_transcript}"
    Return only the corrected, final text and nothing else.
    """
    
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": correction_prompt}]
    )
    corrected_text = response.choices[0].message.content.strip()
    print(f"Step D: Got corrected reference text: '{corrected_text}'")
    return corrected_text

def correct_transcript_text(raw_transcript: str) -> str:
    """
    Takes a raw transcript string and uses an LLM to correct it into clean reference text.
    """
    if not raw_transcript:
        raise HTTPException(status_code=400, detail="No transcript provided for correction.")
    
    print(f"Correcting transcript: '{raw_transcript}'")

    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI client not configured for correction.")

    correction_prompt = f"""
    You are an expert English editor. A student provided a speech transcript that may contain grammatical errors or misrecognized words. 
    Your task is to correct it into a clean, grammatically perfect, and logical sentence or paragraph.
    The raw transcript is: "{raw_transcript}"
    Return only the corrected, final text and nothing else.
    """
    
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": correction_prompt}]
    )
    corrected_text = response.choices[0].message.content.strip()
    print(f"Got corrected reference text: '{corrected_text}'")
    return corrected_text

def get_ai_coach_feedback(transcript: str, topic: str, duration_seconds: float, word_count: int) -> dict:
    if not openai_client:
        return {"error": "OpenAI client not configured."}
    
    words_per_minute = (word_count / duration_seconds) * 60 if duration_seconds > 0 else 0

    # --- HYBRID POSITIVE CARDS + DETAILED FEEDBACK PROMPT ---
    prompt = f"""
    You are an expert, encouraging, and insightful Senior English Tutor providing a detailed analysis of an impromptu speech.
    The user's task was to speak on the topic: "{topic}".
    The transcript is: "{transcript}"

    Your task is to provide a comprehensive, personalized, and actionable evaluation in a valid JSON object.
    You MUST provide a value for every key. For arrays, return ALL relevant items you find. If none, return an empty array.

    CRITICAL INSTRUCTIONS:
    - For vocabulary suggestions: Provide SLIGHTLY more advanced alternatives, not overly complex academic words. Choose words that are naturally used in everyday professional communication.
    - For coherence feedback: When identifying issues, provide SPECIFIC EXAMPLES from the transcript by quoting the exact phrases where the issue occurs.
    - For general feedback: Be balanced - acknowledge strengths AND areas for improvement in each category.

    Here is the required JSON structure. Follow it with 100% accuracy:
    {{
        "positive_highlights": [
            "<string: A specific, positive, and encouraging comment about something they did well.>"
        ],
        "grammar_feedback": "<string: A balanced overview of grammar performance - mention both strengths and areas needing work>",
        "grammar_errors": [
            {{
                "error": "<string: The exact phrase with the ACTUAL grammar error>", 
                "correction": "<string: The corrected phrase>", 
                "explanation": "<string: A detailed explanation of why this is incorrect and what grammar concept is violated>"
            }}
        ],
        "vocabulary_feedback": "<string: A balanced overview of vocabulary usage - mention both effective word choices and opportunities for enhancement>",
        "vocabulary_suggestions": [
            {{
                "original": "<string: A simple phrase from the transcript>",
                "enhanced": "<string: The same phrase with SLIGHTLY more advanced vocabulary (not overly academic)>",
                "explanation": "<string: Explanation of why the enhanced version is more effective>"
            }}
        ],
        "coherence_feedback": "<string: A detailed analysis of the speech's organization and flow. When identifying problems, include SPECIFIC EXAMPLES like 'You jumped from talking about X to Y without transition at...' Include quotes from the transcript.>",
        "fluency_feedback": "<string: A detailed analysis of speaking pace, rhythm, pauses, and flow. Include specific examples of where the student paused too long, spoke too fast/slow, or had good pacing.>",
        "rewritten_sample": "<string: Rewrite the user's ENTIRE speech into an improved version of a SIMILAR LENGTH at an appropriate, slightly more advanced level.>"
    }}
    """
    try:
        response = openai_client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": prompt}], response_format={"type": "json_object"})
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="OpenAI returned malformed JSON.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API Error: {str(e)}")

def get_whisper_transcript(wav_data: bytes) -> str:
    """Sends audio to OpenAI's Whisper API and returns the transcript."""
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI client not configured.")
    try:
        # Whisper API requires a file-like object
        audio_file = io.BytesIO(wav_data)
        audio_file.name = "audio.wav"
        
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        return transcript.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Whisper API Error: {str(e)}")

# --- NEW, CORRECTED VERSION of upload_audio_to_blob ---
async def upload_audio_to_blob(audio_bytes: bytes) -> str:
    """Uploads audio to Azure Blob Storage and returns the SAS URL."""
    connect_str = AZURE_STORAGE_CONNECTION_STRING
    container_name = AZURE_STORAGE_CONTAINER_NAME
    if not connect_str or not container_name:
        raise HTTPException(status_code=500, detail="Azure Storage not configured.")

    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    
    blob_name = f"impromptu_{uuid.uuid4()}.wav"
    
    async with blob_service_client.get_container_client(container_name) as container_client:
        # Create container if it doesn't exist
        try:
            await container_client.create_container()
        except Exception:
            pass # Container likely already exists

        blob_client = container_client.get_blob_client(blob_name)
        await blob_client.upload_blob(io.BytesIO(audio_bytes), overwrite=True)

        # Generate SAS token using the account key
        account_name = blob_service_client.account_name
        account_key = blob_service_client.credential.account_key
        
        sas_token = generate_blob_sas(
            account_name=account_name,
            account_key=account_key,
            container_name=container_name,
            blob_name=blob_name,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=4)
        )
        return f"{blob_client.url}?{sas_token}"

# --- API ENDPOINTS ---

@app.post("/users/signup", response_model=User)
def create_user(user: User, session: Annotated[Session, Depends(get_session)]):
    db_user = session.exec(select(User).where(User.email == user.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.hashed_password)
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role=user.role
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

class Token(SQLModel):
    access_token: str
    token_type: str

@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)]
):
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

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
    elif mode == 'impromptu_experimental':
        # This new mode implements the dynamic reference text workflow
        corrected_reference_text = generate_dynamic_reference_text(wav_data)
        
        # Now, use the corrected text to perform a standard pronunciation assessment
        azure_data = get_pronunciation_assessment(wav_data, corrected_reference_text)
        
        # We add the generated text to the response so we can see it on the frontend
        response_data = azure_data.get("NBest")[0]
        response_data["GeneratedReferenceText"] = corrected_reference_text
        
        return JSONResponse(content={"mode": "pronunciation", "azureAssessment": response_data})
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

@app.post("/api/analyze-chunked")
async def analyze_chunked_speech(audio_file: UploadFile = File(...), topic: str = Form(...)):
    audio_bytes = await audio_file.read()
    
    # ... (the temporary file and initial ffmpeg conversion logic remains the same)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_in, \
         tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_out:
        temp_in.write(audio_bytes)
        temp_in_path = temp_in.name
        temp_out_path = temp_out.name

    try:
        # --- PART 1: GET THE TRANSCRIPT AND PRONUNCIATION ASSESSMENT ---
        
        # First, convert the whole file to a clean WAV
        convert_command = [ FFMPEG_PATH, '-i', temp_in_path, '-ac', '1', '-ar', '16000', temp_out_path, '-y' ]
        subprocess.run(convert_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Get audio duration to determine if we need chunking
        ffprobe_command = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', temp_out_path]
        duration_result = subprocess.run(ffprobe_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        duration_seconds = float(duration_result.stdout.strip().decode())

        # Read full WAV data for pronunciation assessment later
        with open(temp_out_path, 'rb') as f:
            full_wav_data = f.read()

        # Get transcript using chunked processing for long audio
        chunk_length_seconds = 45
        num_chunks = math.ceil(duration_seconds / chunk_length_seconds)
        
        if num_chunks <= 1:
            # Short audio - single STT call
            print(f"Short audio ({duration_seconds:.1f}s) - using single STT call")
            raw_stt_result = get_stt_result(full_wav_data)
            raw_transcript = raw_stt_result.get("DisplayText", "")
        else:
            # Long audio - chunked parallel processing
            print(f"Long audio ({duration_seconds:.1f}s) - using {num_chunks} chunks for transcription")
            
            tasks = []
            for i in range(num_chunks):
                start_time = i * chunk_length_seconds
                print(f"Processing chunk {i+1}/{num_chunks} (start: {start_time}s)")
                chunk_command = [ FFMPEG_PATH, '-i', temp_out_path, '-ss', str(start_time), '-t', str(chunk_length_seconds), '-f', 'wav', 'pipe:1' ]
                try:
                    process = subprocess.run(chunk_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                    wav_data = process.stdout
                    if wav_data:
                        print(f"Chunk {i+1} audio size: {len(wav_data)} bytes")
                        tasks.append(process_chunk_async(wav_data))
                    else:
                        print(f"Warning: Chunk {i+1} has no audio data")
                except subprocess.CalledProcessError as e:
                    print(f"Error processing chunk {i+1}: {e.stderr.decode()}")
                    raise HTTPException(status_code=500, detail=f"FFmpeg chunk processing failed: {e.stderr.decode()}")

            if not tasks:
                raise HTTPException(status_code=400, detail="No valid audio chunks were created")

            print(f"Starting parallel processing of {len(tasks)} chunks...")
            try:
                # Process all chunks in parallel
                chunk_results = await asyncio.gather(*tasks)
                print(f"Completed parallel chunk processing. Got {len(chunk_results)} results.")
            except Exception as e:
                print(f"Error in parallel chunk processing: {str(e)}")
                raise HTTPException(status_code=502, detail=f"Chunk processing failed: {str(e)}")
            
            # Stitch transcripts together
            transcript_parts = []
            for i, result in enumerate(chunk_results):
                transcript_text = result.get("DisplayText", "") if result else ""
                print(f"Chunk {i+1} transcript: '{transcript_text[:50]}{'...' if len(transcript_text) > 50 else ''}'")
                transcript_parts.append(transcript_text)
            
            raw_transcript = " ".join(transcript_parts).strip()
            print(f"Final stitched transcript length: {len(raw_transcript)} characters")
        
        if not raw_transcript:
            raise HTTPException(status_code=400, detail="Could not detect any speech in the audio.")

        # Get the reference text for pronunciation assessment
        if ENABLE_TEXT_CORRECTION:
            print("Text correction enabled - using GPT-4 to clean transcript")
            corrected_reference_text = correct_transcript_text(raw_transcript)
        else:
            print("Text correction disabled - using raw transcript as reference")
            corrected_reference_text = raw_transcript
        
        # Calculate word count (duration already calculated above)
        word_count = len(raw_transcript.split())
        
        # --- PART 2: RUN PRONUNCIATION AND AI COACH IN PARALLEL ---
        
        print("Starting parallel pronunciation and AI coach analysis...")
        try:
            # For pronunciation assessment, use only first 60 seconds of audio to avoid API limits
            if duration_seconds > 60:
                print(f"Audio is {duration_seconds:.1f}s, truncating to first 60s for pronunciation assessment")
                # Create truncated audio for pronunciation
                truncate_command = [FFMPEG_PATH, '-i', temp_out_path, '-t', '60', '-f', 'wav', 'pipe:1']
                truncate_process = subprocess.run(truncate_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                pronunciation_audio = truncate_process.stdout
                
                # Also truncate the reference text to match the audio duration
                words_per_second = len(raw_transcript.split()) / duration_seconds
                estimated_words_60s = int(words_per_second * 60)
                truncated_reference = " ".join(raw_transcript.split()[:estimated_words_60s])
                print(f"Truncated reference text from {len(raw_transcript)} to {len(truncated_reference)} characters")
            else:
                pronunciation_audio = full_wav_data
                truncated_reference = corrected_reference_text
            
            # Create tasks for parallel execution
            pron_task = asyncio.create_task(
                asyncio.to_thread(get_pronunciation_assessment, pronunciation_audio, truncated_reference)
            )
            coach_task = asyncio.create_task(
                asyncio.to_thread(get_ai_coach_feedback, raw_transcript, topic, duration_seconds, word_count)
            )
            
            # Wait for both to complete
            pronunciation_data, ai_coach_analysis = await asyncio.gather(pron_task, coach_task)
            print("Completed parallel pronunciation and AI coach analysis")
        except Exception as e:
            print(f"Error in parallel final analysis: {str(e)}")
            raise HTTPException(status_code=502, detail=f"Final analysis failed: {str(e)}")
        
        # Add reference text info to response
        if ENABLE_TEXT_CORRECTION:
            pronunciation_data["GeneratedReferenceText"] = corrected_reference_text
        else:
            pronunciation_data["GeneratedReferenceText"] = f"Text correction disabled. Using original transcript: {raw_transcript}"
        
        # --- PART 3: COMBINE AND RETURN ---
        final_result = {
            "mode": "impromptu-combined",
            "transcript": raw_transcript,
            "pronunciationAssessment": pronunciation_data.get("NBest")[0],
            "aiCoachAnalysis": ai_coach_analysis
        }
        return JSONResponse(content=final_result)

    finally:
        # Clean up BOTH temporary files
        os.remove(temp_in_path)
        os.remove(temp_out_path)

# --- NEW: BATCH ANALYSIS ENDPOINT WITH ENHANCED LOGGING ---
@app.post("/api/analyze-batch/start")
async def start_batch_analysis(audio_file: UploadFile = File(...)):
    """Starts a batch transcription job for a long audio file."""
    wav_data = convert_audio_with_ffmpeg(await audio_file.read())
    audio_url = await upload_audio_to_blob(wav_data)

    batch_transcription_endpoint = f"https://{AZURE_SPEECH_REGION}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions"
    
    payload = {
        "contentUrls": [audio_url],
        "properties": {"wordLevelTimestampsEnabled": True},
        "locale": "en-US",
        "displayName": f"Impromptu analysis job {uuid.uuid4()}"
    }
    headers = {'Ocp-Apim-Subscription-Key': AZURE_SPEECH_KEY, 'Content-Type': 'application/json'}
    
    response = requests.post(batch_transcription_endpoint, headers=headers, json=payload)
    
    # ENHANCED LOGGING: We will now see the exact error from Azure
    if response.status_code != 201:
        print("\n" + "#"*50)
        print("### AZURE BATCH API FAILED TO START JOB ###")
        print(f"### STATUS CODE: {response.status_code}")
        print(f"### RESPONSE BODY: {response.text}")
        print("#"*50 + "\n")
        raise HTTPException(status_code=response.status_code, detail=f"Azure Batch API Error: {response.text}")
    
    job_url = response.json()["self"]
    job_id = job_url.split('/')[-1]
    
    return {"jobId": job_id}

@app.get("/api/analyze-batch/status")
async def get_batch_status(job_id: str):
    """Polls the status of an ongoing batch transcription job."""
    status_endpoint = f"https://{AZURE_SPEECH_REGION}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions/{job_id}"
    headers = {'Ocp-Apim-Subscription-Key': AZURE_SPEECH_KEY}
    response = requests.get(status_endpoint, headers=headers)
    response.raise_for_status()
    return response.json()

@app.get("/api/analyze-batch/results")
async def get_batch_results(job_id: str, topic: str):
    """Fetches the final results of a completed batch job and analyzes them."""
    results_endpoint = f"https://{AZURE_SPEECH_REGION}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions/{job_id}/files"
    headers = {'Ocp-Apim-Subscription-Key': AZURE_SPEECH_KEY}
    response = requests.get(results_endpoint, headers=headers)
    response.raise_for_status()
    
    files = response.json().get("values", [])
    if not files:
        raise HTTPException(status_code=404, detail="Transcription result files not found.")
        
    result_file_url = files[0]["links"]["contentUrl"]
    result_content = requests.get(result_file_url).json()
    
    # --- THIS IS THE FIX ---
    # The batch API result uses the "display" key for the transcript, not "lexical".
    transcript_phrases = []
    for phrase in result_content.get("recognizedPhrases", []):
        transcript_phrases.append(phrase.get("display", ""))
    transcript = " ".join(transcript_phrases)
    
    # The rest of the function remains the same
    duration_seconds = sum([phrase.get("durationInTicks", 0) for phrase in result_content.get("recognizedPhrases", [])]) / 10000000.0
    word_count = len(transcript.split())
    
    ai_coach_analysis = get_ai_coach_feedback(transcript, topic, duration_seconds, word_count)

    final_result = {
        "mode": "impromptu-batch",
        "transcript": transcript,
        "azureMetrics": {"wordCount": word_count, "duration": duration_seconds},
        "aiCoachAnalysis": ai_coach_analysis
    }
    return JSONResponse(content=final_result)

@app.post("/api/analyze-ab-test")
async def analyze_ab_test(audio_file: UploadFile = File(...), topic: str = Form("General Speaking")):
    """
    Runs a comprehensive A/B test by getting transcripts from both Azure and Whisper,
    then running pronunciation assessments and AI coach analysis on both.
    """
    audio_bytes = await audio_file.read()
    wav_data = convert_audio_with_ffmpeg(audio_bytes)

    # --- Step 1: Get transcripts from both services ---
    transcript_azure = get_stt_result(wav_data).get("DisplayText", "")
    transcript_whisper = get_whisper_transcript(wav_data)

    # --- Step 2: Get pronunciation assessments for both transcripts ---
    pronunciation_azure = get_pronunciation_assessment(wav_data, transcript_azure)
    pronunciation_whisper = get_pronunciation_assessment(wav_data, transcript_whisper)

    # --- Step 3: Get AI coach analysis for both transcripts ---
    # Calculate duration for AI coach analysis
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
        temp_wav.write(wav_data)
        temp_wav_path = temp_wav.name
    
    try:
        duration_seconds = float(subprocess.run([FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', temp_wav_path], stdout=subprocess.PIPE, check=True).stdout)
        
        # AI coach analysis for both transcripts
        azure_word_count = len(transcript_azure.split()) if transcript_azure else 0
        whisper_word_count = len(transcript_whisper.split()) if transcript_whisper else 0
        
        ai_coach_azure = get_ai_coach_feedback(transcript_azure, topic, duration_seconds, azure_word_count) if transcript_azure else {"error": "No transcript from Azure"}
        ai_coach_whisper = get_ai_coach_feedback(transcript_whisper, topic, duration_seconds, whisper_word_count) if transcript_whisper else {"error": "No transcript from Whisper"}
        
    finally:
        os.remove(temp_wav_path)

    # --- Step 4: Bundle all results ---
    final_result = {
        "azure_track": {
            "transcript": transcript_azure,
            "pronunciationAssessment": pronunciation_azure.get("NBest")[0],
            "aiCoachAnalysis": ai_coach_azure
        },
        "whisper_track": {
            "transcript": transcript_whisper,
            "pronunciationAssessment": pronunciation_whisper.get("NBest")[0],
            "aiCoachAnalysis": ai_coach_whisper
        }
    }
    return JSONResponse(content=final_result)

# --- THIS MUST BE THE LAST ROUTE DEFINITION ---
app.mount("/", StaticFiles(directory="static", html=True), name="static")