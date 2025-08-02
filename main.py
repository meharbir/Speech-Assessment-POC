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
        
# --- NEW ASYNC HELPER FOR A SINGLE CHUNK ---
async def process_chunk_async(chunk_data: bytes) -> dict:
    """Asynchronously calls the STT API for a single chunk of audio."""
    # In a real-world scenario with high traffic, you might use an async HTTP client like httpx.
    # For our MVP, running the synchronous `requests` call in an async executor is a robust solution.
    loop = asyncio.get_event_loop()
    stt_result = await loop.run_in_executor(None, get_stt_result, chunk_data)
    return stt_result

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

@app.post("/api/analyze-chunked")
async def analyze_chunked_speech(audio_file: UploadFile = File(...), topic: str = Form(...)):
    """
    Analyzes audio by processing chunks in parallel for maximum speed.
    """
    audio_bytes = await audio_file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="The submitted audio file is empty.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_in, \
         tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_out:
        temp_in.write(audio_bytes)
        temp_in_path = temp_in.name
        temp_out_path = temp_out.name
    
    try:
        # Step 1: Convert to WAV and get duration (same as before)
        convert_command = [ FFMPEG_PATH, '-i', temp_in_path, '-ac', '1', '-ar', '16000', temp_out_path, '-y' ]
        subprocess.run(convert_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ffprobe_command = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', temp_out_path]
        duration_result = subprocess.run(ffprobe_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        duration_seconds = float(duration_result.stdout.strip().decode())

        # Step 2: Create audio chunks (same as before)
        chunk_length_seconds = 45
        num_chunks = math.ceil(duration_seconds / chunk_length_seconds)
        
        tasks = []
        for i in range(num_chunks):
            start_time = i * chunk_length_seconds
            chunk_command = [ FFMPEG_PATH, '-i', temp_out_path, '-ss', str(start_time), '-t', str(chunk_length_seconds), '-f', 'wav', 'pipe:1' ]
            process = subprocess.run(chunk_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            wav_data = process.stdout
            if wav_data:
                # Create a task for each chunk
                tasks.append(process_chunk_async(wav_data))

        # --- NEW: Step 3: Run all chunk processing tasks in parallel ---
        chunk_results = await asyncio.gather(*tasks)
        
        # Step 4: Stitch the results together in order
        full_transcript = ""
        total_word_count = 0
        for result in chunk_results:
            full_transcript += result.get("DisplayText", "") + " "
            total_word_count += len(result.get("NBest", [{}])[0].get("Words", []))

        full_transcript = full_transcript.strip()
        if not full_transcript:
            raise HTTPException(status_code=400, detail="Could not detect any speech in the audio.")

        # Step 5: Final analysis with the full transcript (same as before)
        ai_coach_analysis = get_ai_coach_feedback(full_transcript, topic, duration_seconds, total_word_count)
        
        final_result = {
            "mode": "impromptu-chunked",
            "transcript": full_transcript,
            "azureMetrics": {"wordCount": total_word_count, "duration": duration_seconds},
            "aiCoachAnalysis": ai_coach_analysis
        }
        return JSONResponse(content=final_result)

    finally:
        # Step 6: Clean up temporary files (same as before)
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

# --- THIS MUST BE THE LAST ROUTE DEFINITION ---
app.mount("/", StaticFiles(directory="static", html=True), name="static")