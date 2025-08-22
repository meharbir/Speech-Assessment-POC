import os
import json
import uuid
import logging
import socket
import subprocess
import io
import base64
import requests
import math
import tempfile
import asyncio
import secrets
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import OpenAI
import azure.cognitiveservices.speech as speechsdk
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
from sqlmodel import create_engine, SQLModel, select

# --- NEW IMPORTS FOR AUTH ---
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer
from fastapi import Request
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, create_engine, SQLModel
from typing import Annotated, List
from datetime import datetime, timedelta, timezone
# --- END NEW IMPORTS ---

from models import User, Session as DBSession, Topic, Class # Renamed to avoid conflict
from rubrics import CBSE_ASL_DETAILED_RUBRIC

# --- NEW HYBRID GROQ IMPORTS ---
from groq_service import GroqService
from audio_metrics import AdvancedAudioAnalyzer

# --- CONFIGURATION & INITIALIZATION ---
load_dotenv()
app = FastAPI()

# --- DATABASE CONNECTION ---
DATABASE_URL = os.getenv("DATABASE_URL")
print(f"[DEBUG] DATABASE_URL loaded: {DATABASE_URL}")
print(f"[DEBUG] DATABASE_URL length: {len(DATABASE_URL) if DATABASE_URL else 'None'}")

# Test DNS resolution
try:
    hostname = "db.nfrgfkmvhocucfkoimku.supabase.co"
    print(f"[DEBUG] Testing DNS resolution for {hostname}")
    ip = socket.gethostbyname(hostname)
    print(f"[DEBUG] DNS resolved to IP: {ip}")
except Exception as e:
    print(f"[DEBUG] DNS resolution failed: {e}")

engine = create_engine(DATABASE_URL, echo=True)
print(f"[DEBUG] SQLAlchemy engine created successfully")

def create_db_and_tables():
    print("[DEBUG] Starting create_db_and_tables()")
    try:
        print("[DEBUG] About to call SQLModel.metadata.create_all(engine)")
        SQLModel.metadata.create_all(engine)
        print("[DEBUG] Database tables created successfully!")
    except Exception as e:
        print(f"[DEBUG] Database table creation failed: {e}")
        raise

async def run_ping_task():
    """Periodically sends a ping to all connected WebSocket clients."""
    while True:
        await asyncio.sleep(20) # Send a ping every 20 seconds
        await manager.send_ping()

# Connect to the database and create tables on startup
@app.on_event("startup")
def on_startup():
    print("[DEBUG] FastAPI startup event triggered")
    create_db_and_tables()
    # Start the ping task as a background task
    asyncio.create_task(run_ping_task())
    print("[DEBUG] Startup completed successfully and ping task started")

# --- SECURITY CONFIGURATION ---
SECRET_KEY = os.getenv("SECRET_KEY", "a_super_secret_dev_key_change_this") # CHANGE IN PRODUCTION
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
oauth2_scheme_optional = HTTPBearer(auto_error=False)

# --- HELPER & DEPENDENCY FUNCTIONS ---
def get_session():
    with Session(engine) as session:
        yield session

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def generate_class_code():
    """Generates a simple, shareable 6-character class code."""
    return f"{secrets.token_hex(3).upper()}"

# --- WEBSOCKET CONNECTION MANAGER ---
# --- ENHANCED WEBSOCKET CONNECTION MANAGER ---
class ConnectionManager:
    def __init__(self):
        # We now store websockets in a more structured way
        self.active_connections: dict[int, dict[str, list[WebSocket]]] = {}

    async def connect(self, websocket: WebSocket, class_id: int, user: User):
        await websocket.accept()
        if class_id not in self.active_connections:
            self.active_connections[class_id] = {"teacher": [], "student": []}
        
        # Add the connection to the appropriate list based on role
        self.active_connections[class_id][user.role].append(websocket)

    def disconnect(self, websocket: WebSocket, class_id: int, user: User):
        if class_id in self.active_connections:
            self.active_connections[class_id][user.role].remove(websocket)

    async def send_to_teacher(self, message: str, class_id: int):
        # Now we send specifically to the teacher's connection
        if class_id in self.active_connections:
            for connection in self.active_connections[class_id]["teacher"]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    # Connection might be closed or dead, skip it
                    print(f"⚠️ Could not send to teacher: {e}")
                    pass
    
    async def broadcast_to_class(self, message: str, class_id: int):
        # Now we can broadcast to just students
        if class_id in self.active_connections:
            for connection in self.active_connections[class_id]["student"]:
                await connection.send_text(message)

    async def send_ping(self):
        for class_id, role_connections in self.active_connections.items():
            for role, connections in role_connections.items():
                for connection in connections:
                    try:
                        await connection.send_text('{"type": "ping"}')
                    except Exception:
                        # If sending fails, the connection is likely dead.
                        # The main receive loop will handle the disconnect.
                        pass

manager = ConnectionManager()

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)]
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None:
        raise credentials_exception
    return user

async def get_optional_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme_optional)] = None,
    session: Annotated[Session, Depends(get_session)] = None
) -> User | None:
    if token is None:
        return None
        
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except (JWTError, AttributeError):
        return None
    
    user = session.exec(select(User).where(User.email == email)).first()
    return user

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

# --- HYBRID GROQ SERVICE INITIALIZATION ---
groq_service = GroqService()
audio_analyzer = AdvancedAudioAnalyzer()

# --- HELPER FUNCTIONS ---

def make_json_serializable(obj):
    """
    Recursively convert an object to make it JSON serializable.
    Handles numpy types, booleans, and other non-serializable objects.
    """
    if obj is None:
        return None
    elif isinstance(obj, bool):
        return bool(obj)  # Ensure it's a Python bool, not numpy.bool_
    elif isinstance(obj, (int, float, str)):
        return obj
    elif hasattr(obj, 'item'):  # numpy scalars
        return obj.item()
    elif hasattr(obj, 'tolist'):  # numpy arrays
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: make_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    else:
        # For any other type, try to convert to string
        return str(obj)

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
        
        # DETAILED DEBUG: Print the COMPLETE Azure response
        print(f"\n{'#'*80}")
        print(f"COMPLETE AZURE PRONUNCIATION RESPONSE:")
        print(f"{'#'*80}")
        print(json.dumps(result, indent=2))
        print(f"{'#'*80}\n")
        
        # Debug: Print what Azure actually returns
        if result.get("NBest") and len(result["NBest"]) > 0:
            nbest = result["NBest"][0]
            print(f"Azure Pronunciation Scores Received:")
            print(f"  - PronunciationScore: {nbest.get('PronunciationScore', 'NOT FOUND')}")
            print(f"  - AccuracyScore: {nbest.get('AccuracyScore', 'NOT FOUND')}")
            print(f"  - FluencyScore: {nbest.get('FluencyScore', 'NOT FOUND')}")
            print(f"  - ProsodyScore: {nbest.get('ProsodyScore', 'NOT FOUND')}")
            print(f"  - CompletenessScore: {nbest.get('CompletenessScore', 'NOT FOUND')}")
            
            # Check for Words array and phoneme data
            if 'Words' in nbest:
                print(f"  - Words array found with {len(nbest['Words'])} words")
                if len(nbest['Words']) > 0:
                    first_word = nbest['Words'][0]
                    print(f"  - First word structure: {json.dumps(first_word, indent=4)}")
            else:
                print(f"  - Words array: NOT FOUND")
        
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

    prompt = f"""
    You are an expert AI English Tutor for a student in India. Your task is to provide a comprehensive evaluation of their impromptu speech based on the official CBSE ASL rubric. Your final scores MUST be converted to a 100-point scale (e.g., a rubric score of 4/5 is 80/100).

    --- OFFICIAL CBSE ASL DETAILED RUBRIC ---
    {CBSE_ASL_DETAILED_RUBRIC}
    --- END OF RUBRIC ---

    The student was asked to speak on the topic: "{topic}".
    The student's transcript is: "{transcript}"

    You MUST evaluate the transcript strictly against the provided detailed rubric. Your feedback and scores must directly reflect the criteria outlined. Provide at least 3-5 vocabulary enhancement suggestions with specific words/phrases from the transcript. For the detailed analysis, combine fluency and coherence insights with concrete examples. Provide your full analysis in a valid JSON object with the following structure:

    {{
        "relevance_score": <integer from 0-100, based on the 'INTERACTION' rubric criteria>,
        "relevance_feedback": "<string: A personalized comment on how well the student's contribution was relevant to the topic, referencing the rubric.>",
        "fluency_score": <integer from 0-100, based on the 'FLUENCY & COHERENCE' rubric criteria>,
        "fluency_feedback": "<string: Personalized comment on pace, rhythm, and coherence, referencing the rubric.>",
        "pronunciation_score": <integer from 0-100, based on the 'PRONUNCIATION' rubric criteria>,
        "pronunciation_feedback": "<string: A summary of the student's pronunciation and articulation clarity, referencing the rubric.>",
        "grammar_score": <integer from 0-100, based on the 'LANGUAGE' rubric criteria for grammar>,
        "grammar_errors": [
            {{"error": "<string: Phrase with error>", "correction": "<string: Corrected phrase>", "explanation": "<string: Simple explanation>"}}
        ],
        "vocabulary_score": <integer from 0-100, based on the 'LANGUAGE' rubric criteria for vocabulary>,
        "vocabulary_feedback": "<string: Personalized comment on word choice, referencing the rubric.>",
        "vocabulary_suggestions": [
            {{"original": "<string: word/phrase from transcript>", "enhanced": "<string: better alternative>", "explanation": "<string: why it's better>"}}
        ],
        "detailed_fluency_coherence_analysis": "<string: Combined detailed analysis of both fluency and coherence with specific examples from the transcript, referencing the CBSE rubric criteria>",
        "positive_highlights": [
            "<string: A specific, positive comment aligned with the rubric's goals.>"
        ],
        "rewritten_sample": "<string: Rewrite the user's speech into an improved version that would score higher against the rubric.>"
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

def get_ai_class_summary(session_data: list, topic: str) -> dict:
    """
    Analyzes a list of session feedback data to generate a class-wide summary.
    """
    if not openai_client:
        return {"error": "OpenAI client not configured."}

    # Aggregate all the feedback into a single structure for the AI
    aggregated_feedback = json.dumps(session_data, indent=2)

    prompt = f"""
    You are an expert educational analyst for a school in India. Your task is to analyze aggregated AI feedback from an entire class for a speaking session on the topic "{topic}". Your analysis MUST be based on the official CBSE ASL rubric.

    --- OFFICIAL CBSE ASL RUBRIC ---
    {CBSE_ASL_DETAILED_RUBRIC}
    --- END OF RUBRIC ---

    Here is the aggregated data from individual student analyses:
    {aggregated_feedback}

    Based on this data, identify the most significant, common patterns of strengths and weaknesses across the entire class, according to the rubric. Provide your analysis in a valid JSON object with the following structure:

    {{
        "strengths": [
            "<string: Identify the most prominent shared strength, referencing a specific rubric criterion. e.g., 'The class demonstrated strong Fluency, with most students speaking at a consistent pace.'>"
        ],
        "weaknesses": [
            "<string: Identify the most common shared weakness, referencing a specific rubric criterion and providing an example. e.g., 'The most common Language issue was incorrect preposition usage, a key point in the grammar assessment.'>"
        ]
    }}
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API Error during summary: {str(e)}")

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
def create_user(
    user: User, 
    session: Annotated[Session, Depends(get_session)],
    class_code: str = Query(None)
):
    db_user = session.exec(select(User).where(User.email == user.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    class_id = None
    if user.role == 'student':
        if not class_code:
            raise HTTPException(status_code=400, detail="Students must provide a class code.")
        
        # Ensure class_code is uppercase for consistent matching
        target_class = session.exec(select(Class).where(Class.class_code == class_code.upper())).first()
        if not target_class:
            raise HTTPException(status_code=404, detail="Invalid Class Code.")
        class_id = target_class.id
    
    # Teachers do not need a class_code to sign up
    elif user.role != 'teacher':
        raise HTTPException(status_code=400, detail="Invalid user role specified.")

    hashed_password = get_password_hash(user.hashed_password)
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role=user.role,
        class_id=class_id
    )
    session.add(db_user)
    
    try:
        session.commit()
        session.refresh(db_user)
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
        
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

@app.get("/api/users/me", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    """
    Fetch the currently authenticated user.
    """
    return current_user

class ClassCreate(BaseModel):
    name: str

class TopicBroadcast(BaseModel):
    mode: str
    text: str

class JoinClassRequest(BaseModel):
    class_code: str

@app.post("/api/teacher/classes", response_model=Class)
async def create_class(
    class_data: ClassCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Allows a logged-in teacher to create a new class."""
    if current_user.role != 'teacher':
        raise HTTPException(status_code=403, detail="Only teachers can create classes.")
    
    new_class = Class(
        name=class_data.name,
        class_code=generate_class_code(),
        teacher_id=current_user.id
    )
    session.add(new_class)
    session.commit()
    session.refresh(new_class)
    
    # Assign the teacher to their own class
    current_user.class_id = new_class.id
    session.add(current_user)
    session.commit()
    
    return new_class

@app.post("/api/teacher/class/topic")
async def broadcast_topic(
    topic_data: TopicBroadcast,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    if current_user.role != 'teacher':
        raise HTTPException(status_code=403, detail="Only teachers can broadcast topics.")
    
    teacher_class = session.exec(select(Class).where(Class.teacher_id == current_user.id)).first()
    if not teacher_class:
        raise HTTPException(status_code=404, detail="Teacher has not created a class yet.")
        
    message = {
        "type": "new_topic",
        "payload": {
            "mode": topic_data.mode,
            "text": topic_data.text
        }
    }
    
    await manager.broadcast_to_class(json.dumps(message), teacher_class.id)
    return {"status": "Topic broadcasted successfully"}

@app.get("/api/teacher/my-class", response_model=Class)
async def get_teacher_class(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Fetches the class taught by the currently logged-in teacher."""
    if current_user.role != 'teacher':
        raise HTTPException(status_code=403, detail="User is not a teacher.")
    
    teacher_class = session.exec(select(Class).where(Class.teacher_id == current_user.id)).first()
    
    if not teacher_class:
        raise HTTPException(status_code=404, detail="Teacher has not created a class yet.")
        
    return teacher_class

@app.get("/api/teacher/students")
async def get_teacher_students(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Fetches all students in the teacher's class."""
    if current_user.role != 'teacher':
        raise HTTPException(status_code=403, detail="User is not a teacher.")
    
    teacher_class = session.exec(select(Class).where(Class.teacher_id == current_user.id)).first()
    
    if not teacher_class:
        raise HTTPException(status_code=404, detail="Teacher has not created a class yet.")
    
    students = session.exec(select(User).where(User.class_id == teacher_class.id, User.role == 'student')).all()
    
    return [{"id": student.id, "full_name": student.full_name, "email": student.email} for student in students]

@app.get("/api/teacher/student/{student_id}/sessions", response_model=List[DBSession])
async def get_student_sessions_for_teacher(
    student_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Fetches all practice sessions for a specific student,
    ensuring the requesting user is that student's teacher.
    """
    if current_user.role != 'teacher':
        raise HTTPException(status_code=403, detail="Only teachers can view student sessions.")

    # Find the student and verify they exist
    student = session.get(User, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    # Security Check: Verify the student is in the current teacher's class
    if not student.student_class or student.student_class.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: Student is not in your class.")
        
    return student.sessions

class ClassSummaryRequest(BaseModel):
    topic: str

@app.post("/api/teacher/class/summary", response_model=dict)
async def get_class_summary(
    summary_request: ClassSummaryRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Generates an AI-powered summary of class performance for a specific topic.
    """
    if current_user.role != 'teacher':
        raise HTTPException(status_code=403, detail="Only teachers can generate summaries.")
    
    teacher_class = session.exec(select(Class).where(Class.teacher_id == current_user.id)).first()
    if not teacher_class:
        raise HTTPException(status_code=404, detail="Teacher has no class.")

    # Find all sessions for this topic from students in the teacher's class
    student_ids = [student.id for student in teacher_class.students]
    relevant_sessions = session.exec(
        select(DBSession)
        .where(DBSession.student_id.in_(student_ids))
        .where(DBSession.topic == summary_request.topic)
    ).all()

    if not relevant_sessions:
        raise HTTPException(status_code=404, detail="No student sessions found for this topic.")

    # Extract just the feedback data for analysis
    feedback_data = [json.loads(s.feedback_json)["data"] for s in relevant_sessions if s.feedback_json]
    
    summary = get_ai_class_summary(feedback_data, summary_request.topic)
    return summary

@app.patch("/api/student/join-class", response_model=User)
async def join_class(
    join_request: JoinClassRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Allows a logged-in student to join a class using a class code."""
    if current_user.role != 'student':
        raise HTTPException(status_code=403, detail="Only students can join a class.")
    
    if current_user.class_id:
        raise HTTPException(status_code=400, detail="Student is already in a class.")

    class_code = join_request.class_code.upper()
    target_class = session.exec(select(Class).where(Class.class_code == class_code)).first()

    if not target_class:
        raise HTTPException(status_code=404, detail="Invalid Class Code.")

    # Update the user's class_id
    current_user.class_id = target_class.id
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return current_user

@app.get("/api/me/sessions")
async def get_user_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Fetches all practice sessions for the currently logged-in user.
    """
    try:
        print(f"Fetching sessions for user: {current_user.id}")
        user_with_sessions = session.get(User, current_user.id)
        print(f"User found: {user_with_sessions}")
        sessions = user_with_sessions.sessions if user_with_sessions else []
        print(f"Number of sessions: {len(sessions)}")
        
        # Convert to dict to avoid Pydantic model issues
        sessions_data = []
        for s in sessions:
            try:
                session_dict = {
                    "id": s.id,
                    "topic": s.topic,
                    "transcript": s.transcript,
                    "feedback_json": s.feedback_json,
                    "created_at": s.created_at,
                    "student_id": s.student_id
                }
                sessions_data.append(session_dict)
            except Exception as e:
                print(f"Error processing session {s.id}: {e}")
                continue
        
        print(f"Returning {len(sessions_data)} sessions")
        return sessions_data
    except Exception as e:
        print(f"Error in get_user_sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/analyze")
async def analyze_speech(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    mode: str = Query(...),
    audio_file: UploadFile = File(...),
    reference_text: str = Form(None),
    topic: str = Form(None)
):
    audio_bytes = await audio_file.read()
    wav_data = convert_audio_with_ffmpeg(audio_bytes)

    if mode == 'pronunciation':
        if not reference_text:
            raise HTTPException(status_code=400, detail="Reference text required.")
        
        azure_data = get_pronunciation_assessment(wav_data, reference_text)
        
        if azure_data.get("RecognitionStatus") == "Success" and azure_data.get("NBest"):
            detailed_result = azure_data["NBest"][0]
            
            if "PronScore" in detailed_result:
                detailed_result["PronunciationScore"] = detailed_result["PronScore"]

            if current_user:
                # Save the session using the new standardized wrapper
                serializable_result = make_json_serializable(detailed_result)
                db_session = DBSession(
                    topic="Pronunciation Practice",
                    transcript=detailed_result.get("Display"),
                    feedback_json=json.dumps({"type": "pronunciation", "data": serializable_result}),
                    student_id=current_user.id
                )
                session.add(db_session)
                session.commit()

            return JSONResponse(content={"mode": "pronunciation", "azureAssessment": make_json_serializable(detailed_result)})
        else:
            error_detail = azure_data.get("DisplayText", "Azure API returned an unsuccessful status.")
            raise HTTPException(status_code=502, detail=f"Pronunciation assessment failed: {error_detail}")

    elif mode == 'impromptu':
        if not topic: raise HTTPException(status_code=400, detail="Topic is required.")
        stt_result = get_stt_result(wav_data)
        transcript = stt_result.get("DisplayText", "")
        if not transcript: raise HTTPException(status_code=400, detail="Could not detect speech.")
        
        nbest = stt_result.get("NBest", [{}])[0]
        duration_seconds = nbest.get("Duration", 0) / 10000000.0
        word_count = len(nbest.get("Words", []))
        
        ai_coach_analysis = get_ai_coach_feedback(transcript, topic, duration_seconds, word_count)
        
        if current_user:
            # Save the session using the new standardized wrapper
            serializable_analysis = make_json_serializable(ai_coach_analysis)
            db_session = DBSession(
                topic=topic,
                transcript=transcript,
                feedback_json=json.dumps({"type": "impromptu", "data": serializable_analysis}),
                student_id=current_user.id
            )
            session.add(db_session)
            session.commit()

        final_result = { "mode": "impromptu", "transcript": transcript, "azureMetrics": { "wordCount": word_count, "duration": duration_seconds }, "aiCoachAnalysis": ai_coach_analysis }
        return JSONResponse(content=make_json_serializable(final_result))
    
    else:
        raise HTTPException(status_code=400, detail="Invalid analysis mode specified.")

# UPDATED Text-to-Speech Endpoint for single words
@app.get("/api/synthesize")
async def synthesize_speech(
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    word: str = Query(...)
):
    if not word: raise HTTPException(status_code=400, detail="No word provided.")
    
    speech_config.speech_synthesis_voice_name = "en-IN-NeerjaNeural"
    
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
async def synthesize_paragraph(
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    item: TextToSynthesize = None
):
    if not item.text:
        raise HTTPException(status_code=400, detail="No text provided.")
    
    speech_config.speech_synthesis_voice_name = "en-IN-NeerjaNeural"
    
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    result = synthesizer.speak_text_async(item.text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return StreamingResponse(io.BytesIO(result.audio_data), media_type="audio/wav")
    else:
        raise HTTPException(status_code=500, detail=f"TTS Canceled: {result.cancellation_details.reason}")

@app.post("/api/analyze-chunked")
async def analyze_chunked_speech(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    audio_file: UploadFile = File(...), 
    topic: str = Form(...)
):
    """
    Analyzes audio for a logged-in user or a guest.
    Saves the session to the database ONLY if the user is logged in.
    """
    audio_bytes = await audio_file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="The submitted audio file is empty.")

    # We are keeping the core audio processing logic the same
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_in, \
         tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_out:
        temp_in.write(audio_bytes)
        temp_in_path = temp_in.name
        temp_out_path = temp_out.name
    
    try:
        convert_command = [ FFMPEG_PATH, '-i', temp_in_path, '-ac', '1', '-ar', '16000', temp_out_path, '-y' ]
        subprocess.run(convert_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ffprobe_command = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', temp_out_path]
        duration_result = subprocess.run(ffprobe_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        duration_seconds = float(duration_result.stdout.strip().decode())

        chunk_length_seconds = 45
        num_chunks = math.ceil(duration_seconds / chunk_length_seconds)
        
        tasks = []
        for i in range(num_chunks):
            start_time = i * chunk_length_seconds
            chunk_command = [ FFMPEG_PATH, '-i', temp_out_path, '-ss', str(start_time), '-t', str(chunk_length_seconds), '-f', 'wav', 'pipe:1' ]
            process = subprocess.run(chunk_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            wav_data = process.stdout
            if wav_data:
                tasks.append(process_chunk_async(wav_data))

        chunk_results = await asyncio.gather(*tasks)
        
        full_transcript = ""
        total_word_count = 0
        for result in chunk_results:
            full_transcript += result.get("DisplayText", "") + " "
            total_word_count += len(result.get("NBest", [{}])[0].get("Words", []))

        full_transcript = full_transcript.strip()
        if not full_transcript:
            raise HTTPException(status_code=400, detail="Could not detect any speech in the audio.")

        ai_coach_analysis = get_ai_coach_feedback(full_transcript, topic, duration_seconds, total_word_count)
        
        # --- MODIFIED DATABASE SAVING LOGIC ---
        if current_user:
            # Save the session using the standardized {"type": "...", "data": ...} wrapper
            serializable_analysis = make_json_serializable(ai_coach_analysis)
            db_session = DBSession(
                topic=topic,
                transcript=full_transcript,
                feedback_json=json.dumps({"type": "impromptu", "data": serializable_analysis}),
                student_id=current_user.id
            )
            session.add(db_session)
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                print(f"DATABASE SAVE FAILED for user {current_user.id}: {e}")
        # --- END MODIFIED LOGIC ---

        final_result = {
            "mode": "impromptu-chunked",
            "transcript": full_transcript,
            "azureMetrics": {"wordCount": total_word_count, "duration": duration_seconds},
            "aiCoachAnalysis": ai_coach_analysis
        }
        return JSONResponse(content=make_json_serializable(final_result))

    finally:
        os.remove(temp_in_path)
        os.remove(temp_out_path)

# --- NEW: BATCH ANALYSIS ENDPOINT WITH ENHANCED LOGGING ---
@app.post("/api/analyze-batch/start")
async def start_batch_analysis(
    current_user: Annotated[User, Depends(get_current_user)],
    audio_file: UploadFile = File(...)
):
    """Starts a batch transcription job for a long audio file."""
    # ... the rest of the function remains unchanged
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
async def get_batch_status(
    current_user: Annotated[User, Depends(get_current_user)],
    job_id: str
):
    """Polls the status of an ongoing batch transcription job."""
    # ... the rest of the function remains unchanged
    status_endpoint = f"https://{AZURE_SPEECH_REGION}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions/{job_id}"
    headers = {'Ocp-Apim-Subscription-Key': AZURE_SPEECH_KEY}
    response = requests.get(status_endpoint, headers=headers)
    response.raise_for_status()
    return response.json()

@app.get("/api/analyze-batch/results")
async def get_batch_results(
    current_user: Annotated[User, Depends(get_current_user)],
    job_id: str, 
    topic: str
):
    """Fetches the final results of a completed batch job and analyzes them."""
    # ... the rest of the function remains unchanged
    results_endpoint = f"https://{AZURE_SPEECH_REGION}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions/{job_id}/files"
    headers = {'Ocp-Apim-Subscription-Key': AZURE_SPEECH_KEY}
    response = requests.get(results_endpoint, headers=headers)
    response.raise_for_status()
    
    files = response.json().get("values", [])
    if not files:
        raise HTTPException(status_code=404, detail="Transcription result files not found.")
        
    result_file_url = files[0]["links"]["contentUrl"]
    result_content = requests.get(result_file_url).json()
    
    transcript_phrases = []
    for phrase in result_content.get("recognizedPhrases", []):
        transcript_phrases.append(phrase.get("display", ""))
    transcript = " ".join(transcript_phrases)
    
    duration_seconds = sum([phrase.get("durationInTicks", 0) for phrase in result_content.get("recognizedPhrases", [])]) / 10000000.0
    word_count = len(transcript.split())
    
    ai_coach_analysis = get_ai_coach_feedback(transcript, topic, duration_seconds, word_count)

    final_result = {
        "mode": "impromptu-batch",
        "transcript": transcript,
        "azureMetrics": {"wordCount": word_count, "duration": duration_seconds},
        "aiCoachAnalysis": ai_coach_analysis
    }
    return JSONResponse(content=make_json_serializable(final_result))

@app.post("/api/analyze-ab-test")
async def analyze_ab_test(
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    audio_file: UploadFile = File(...), 
    topic: str = Form("General Speaking")
):
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
            "pronunciationAssessment": pronunciation_azure.get("NBest")[0] if pronunciation_azure.get("NBest") else {},
            "aiCoachAnalysis": ai_coach_azure
        },
        "whisper_track": {
            "transcript": transcript_whisper,
            "pronunciationAssessment": pronunciation_whisper.get("NBest")[0] if pronunciation_whisper.get("NBest") else {},
            "aiCoachAnalysis": ai_coach_whisper
        }
    }
    return JSONResponse(content=make_json_serializable(final_result))

@app.websocket("/ws/{class_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    class_id: int,
    token: str = Query(...),
    session: Session = Depends(get_session) # Get a DB session
):
    """
    Handles WebSocket connections for a specific class.
    Authenticates the user via a JWT token passed as a query parameter.
    """
    try:
        # Use a simplified version of get_current_user to validate the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            await websocket.close(code=1008)
            return
        
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            # User not found
            await websocket.close(code=1008)
            return
        
        # Check if user can access this class
        if user.role == 'teacher':
            # Teacher can connect to classes they teach
            teacher_class = session.exec(select(Class).where(Class.teacher_id == user.id).where(Class.id == class_id)).first()
            if not teacher_class:
                await websocket.close(code=1008)
                return
        elif user.class_id != class_id:
            # Students must belong to the class
            await websocket.close(code=1008)
            return
            
    except JWTError:
        # Token is invalid
        await websocket.close(code=1008)
        return

    # If authentication is successful, connect the user with their role
    await manager.connect(websocket, class_id, user)
    print(f"User {user.full_name} (Role: {user.role}) connected to class {class_id}")
    
    # If a student connects, immediately notify the teacher
    if user.role == 'student':
        connection_message = {
            "type": "student_status_update",
            "payload": {
                "student_id": user.id,
                "student_name": user.full_name,
                "status": "connected"
            }
        }
        await manager.send_to_teacher(json.dumps(connection_message), class_id)
        print(f"📡 WebSocket: Notified teacher that {user.full_name} is connected")
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # If a student sends a status update, relay it to the teacher.
            if message.get("type") == "status_update":
                print(f"📡 WebSocket: Student {user.full_name} sent status: {message.get('status')}")
                update_message = {
                    "type": "student_status_update",
                    "payload": {
                        "student_id": user.id,
                        "student_name": user.full_name,
                        "status": message.get("status")
                    }
                }
                print(f"📡 WebSocket: Relaying to teacher in class {class_id}")
                await manager.send_to_teacher(json.dumps(update_message), class_id)

            # Keep the pong response for our heartbeat
            elif message.get("type") == "pong":
                pass
    except WebSocketDisconnect:
        # On disconnect, send a final status update and then disconnect
        if user.role == 'student':
            disconnect_message = {
                "type": "student_status_update",
                "payload": { "student_id": user.id, "student_name": user.full_name, "status": "disconnected" }
            }
            await manager.send_to_teacher(json.dumps(disconnect_message), class_id)
        
        manager.disconnect(websocket, class_id, user)
        print(f"User {user.full_name} disconnected from class {class_id}")


def generate_student_friendly_audio_tips(audio_metrics: dict) -> dict:
    """
    Generate age-appropriate, actionable tips for 6th graders based on audio metrics
    """
    tips = {}
    
    # Get assessment scores
    assessments = audio_metrics.get("assessments", {})
    pronunciation = audio_metrics.get("pronunciation_analysis", {})
    fluency = audio_metrics.get("fluency_metrics", {})
    voice_quality = audio_metrics.get("voice_quality", {})
    
    # Pronunciation Tips
    pitch_range = pronunciation.get("pitch_range_hz", 0)
    is_monotonous = pronunciation.get("is_monotonous", False)
    
    if is_monotonous:
        tips["pitch_variety"] = {
            "score": max(0, 100 - 20),  # Reduce score for monotony
            "tip": "Try adding more emotion to your voice! Raise your pitch when asking questions and lower it when making important points. Practice reading dialogue with different character voices!",
            "exercise": "Read a fairy tale aloud, making each character sound different."
        }
    else:
        tips["pitch_variety"] = {
            "score": min(100, (pitch_range / 170) * 100),  # Scale to 100
            "tip": "Great job varying your voice! Your speech has good emotional expression.",
            "exercise": "Keep practicing with storytelling to maintain this variety."
        }
    
    # Fluency Tips  
    speaking_rate = fluency.get("speaking_rate_wpm")
    long_pauses = fluency.get("long_pauses", 0)
    
    fluency_score = 100
    fluency_tip = "Good speaking pace! "
    
    if speaking_rate:
        if speaking_rate < 120:
            fluency_score -= 15
            fluency_tip = "You're speaking a bit slowly. Try to speak more naturally, like you're talking to a friend."
        elif speaking_rate > 160:
            fluency_score -= 10
            fluency_tip = "You're speaking quite fast. Take a breath between sentences to help listeners follow along."
    
    if long_pauses > 0:
        fluency_score -= (long_pauses * 10)
        fluency_tip += f" Try to avoid long pauses ({long_pauses} found). If you need to think, use 'um' briefly or take a quick breath."
    
    tips["speaking_fluency"] = {
        "score": max(0, fluency_score),
        "tip": fluency_tip,
        "exercise": "Practice reading aloud for 5 minutes daily to build natural rhythm."
    }
    
    # Voice Quality Tips
    jitter = voice_quality.get("jitter_percent", 0)
    shimmer = voice_quality.get("shimmer_percent", 0)
    hnr = voice_quality.get("hnr_db", 20)
    
    voice_score = 100
    voice_tip = ""
    
    if jitter > 1.04:
        voice_score -= 15
        voice_tip += "Your voice sounds a bit shaky. "
    
    if shimmer > 3.81:
        voice_score -= 15
        voice_tip += "Your volume varies too much. "
        
    if hnr < 20:
        voice_score -= 20
        voice_tip += "Your voice could be clearer. "
    
    if voice_score < 80:
        voice_tip += "Try sitting up straight, speaking from your belly (not your throat), and opening your mouth wider. Practice saying 'Ahh' like at the doctor!"
        exercise = "Practice tongue twisters: 'Red leather, yellow leather' or 'She sells seashells by the seashore.'"
    else:
        voice_tip = "Excellent voice quality! Your speech is clear and steady."
        exercise = "Keep up the great work! Try reading poetry aloud to maintain your clear voice."
    
    tips["voice_clarity"] = {
        "score": max(0, voice_score),
        "tip": voice_tip,
        "exercise": exercise
    }
    
    return tips


@app.post("/api/analyze-hybrid-groq")
async def analyze_hybrid_groq(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    audio_file: UploadFile = File(...),
    topic: str = Form(...)
):
    """
    Hybrid analysis using Whisper (Groq) + Azure Pronunciation + Groq LLaMA + Advanced Audio Metrics
    
    Flow:
    1. Serial: Get transcript from Groq Whisper
    2. Parallel: Azure pronunciation + Groq LLaMA + Audio metrics
    3. Combine results and save to database if user is logged in
    """
    try:
        # Read audio data
        audio_bytes = await audio_file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="The submitted audio file is empty.")

        print(f"[HYBRID] Starting hybrid Groq analysis for topic: {topic}")
        
        # --- STEP A (SERIAL): Get transcript from Groq Whisper first ---
        print("[STEP A] Transcribing with Groq Whisper...")
        
        # Create temporary file for Groq (it expects a file-like object)
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio.flush()
            
            # Get transcript from Groq Whisper
            with open(temp_audio.name, 'rb') as audio_for_groq:
                transcript = await groq_service.transcribe_with_whisper(audio_for_groq)
        
        # Clean up temp file
        os.unlink(temp_audio.name)
        
        print(f"[STEP A] Transcript obtained: {len(transcript)} characters")
        
        # --- STEP B (PARALLEL): Run three analyses concurrently ---
        print("[STEP B] Running parallel analyses...")
        
        async def azure_pronunciation_task():
            """Azure pronunciation assessment using Groq transcript as reference"""
            print("[AZURE] Starting Azure pronunciation assessment...")
            # Convert audio for Azure (needs WAV format)
            wav_data = convert_audio_with_ffmpeg(audio_bytes)
            result = get_pronunciation_assessment(wav_data, transcript)
            print("[AZURE] Azure pronunciation assessment completed")
            return result
        
        async def groq_language_task():
            """Groq LLaMA language analysis"""
            print("[GROQ] Starting Groq LLaMA language analysis...")
            result = await groq_service.analyze_with_llama(transcript, topic)
            print("[GROQ] Groq LLaMA analysis completed")
            return result
        
        async def audio_metrics_task():
            """Advanced audio metrics analysis"""
            print("[METRICS] Starting advanced audio metrics analysis...")
            result = await audio_analyzer.analyze_comprehensive_metrics(audio_bytes, transcript)
            print("[METRICS] Audio metrics analysis completed")
            return result
        
        async def openai_coach_task():
            """OpenAI AI Coach analysis using same prompts for comparison"""
            print("[OPENAI] Starting OpenAI AI Coach analysis...")
            
            try:
                # Calculate duration and word count for AI coach
                import librosa
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                    wav_data = convert_audio_with_ffmpeg(audio_bytes)
                    temp_wav.write(wav_data)
                    temp_wav.flush()
                    temp_wav_path = temp_wav.name
                
                try:
                    # Get audio duration using librosa (more compatible)
                    audio_array, sample_rate = librosa.load(temp_wav_path, sr=None)
                    duration_seconds = len(audio_array) / sample_rate
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_wav_path):
                        os.unlink(temp_wav_path)
                
                word_count = len(transcript.split())
                
                # Call existing AI coach function
                result = get_ai_coach_feedback(transcript, topic, duration_seconds, word_count)
                print("[OPENAI] OpenAI AI Coach analysis completed")
                return result
                
            except Exception as e:
                print(f"[ERROR] OpenAI coach analysis failed: {e}")
                # Return a fallback structure
                return {
                    "error": str(e),
                    "grammar_score": 0,
                    "vocabulary_score": 0,
                    "grammar_errors": [],
                    "vocabulary_suggestions": [],
                    "fluency_feedback": "Analysis failed",
                    "relevance_feedback": "Analysis failed"
                }
        
        # Run all four tasks in parallel using asyncio.gather
        azure_result, groq_result, audio_metrics, openai_result = await asyncio.gather(
            azure_pronunciation_task(),
            groq_language_task(),
            audio_metrics_task(),
            openai_coach_task(),
            return_exceptions=True
        )
        
        # Check for exceptions in parallel tasks
        if isinstance(azure_result, Exception):
            print(f"[ERROR] Azure analysis failed: {azure_result}")
            azure_result = {"error": str(azure_result)}
        
        if isinstance(groq_result, Exception):
            print(f"[ERROR] Groq analysis failed: {groq_result}")
            groq_result = {"error": str(groq_result)}
        
        if isinstance(audio_metrics, Exception):
            print(f"[ERROR] Audio metrics failed: {audio_metrics}")
            audio_metrics = {"error": str(audio_metrics)}
        
        if isinstance(openai_result, Exception):
            print(f"[ERROR] OpenAI analysis failed: {openai_result}")
            openai_result = {"error": str(openai_result)}
        
        # --- STEP C (COMBINE): Create unified response ---
        print("[STEP C] Combining results...")
        
        # Generate student-friendly tips for audio metrics
        student_friendly_tips = {}
        if not isinstance(audio_metrics, dict) or "error" not in audio_metrics:
            try:
                student_friendly_tips = generate_student_friendly_audio_tips(audio_metrics)
                print("[STEP C] Generated student-friendly audio tips")
            except Exception as e:
                print(f"[WARNING] Failed to generate audio tips: {e}")
                student_friendly_tips = {"error": "Could not generate tips"}
        
        # Add tips to audio metrics
        if isinstance(audio_metrics, dict) and "error" not in audio_metrics:
            audio_metrics["student_friendly_tips"] = student_friendly_tips
        
        combined_result = {
            "transcript": transcript,
            "topic": topic,
            "azure_pronunciation": azure_result,
            "groq_language_analysis": groq_result,
            "openai_coach_analysis": openai_result,
            "audio_metrics": audio_metrics,
            "analysis_metadata": {
                "processing_type": "hybrid_groq",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "services_used": ["groq_whisper", "azure_pronunciation", "groq_llama", "openai_coach", "advanced_audio_metrics"]
            }
        }
        
        # --- DATABASE PERSISTENCE ---
        if current_user:
            print(f"[DATABASE] Saving session to database for user: {current_user.full_name}")
            
            # Make data JSON serializable before saving
            serializable_result = make_json_serializable(combined_result)
            
            # Create database session using standardized wrapper format
            db_session = DBSession(
                topic=topic,
                transcript=transcript,
                feedback_json=json.dumps({
                    "type": "hybrid_groq", 
                    "data": serializable_result
                }),
                student_id=current_user.id
            )
            
            session.add(db_session)
            try:
                session.commit()
                print("[DATABASE] Session saved to database successfully")
            except Exception as e:
                print(f"[ERROR] Database save failed: {e}")
                session.rollback()
        else:
            print("[GUEST] Guest user - session not saved to database")
        
        print("[SUCCESS] Hybrid analysis completed successfully")
        # Return JSON-serializable data to frontend
        return make_json_serializable(combined_result)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"[ERROR] Hybrid analysis failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Hybrid analysis failed: {str(e)}"
        )


# --- THIS MUST BE THE LAST ROUTE DEFINITION ---
app.mount("/", StaticFiles(directory="static", html=True), name="static")