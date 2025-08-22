import os
import json
from groq import Groq
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class GroqService:
    """Service for handling Groq API interactions including Whisper and LLaMA"""
    
    def __init__(self):
        """Initialize Groq client with API key from environment"""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        # Initialize Groq client - v0.4.1 doesn't use proxies parameter
        try:
            self.client = Groq(api_key=api_key)
            logger.info("Groq service initialized successfully")
        except TypeError as e:
            # Fallback for different Groq versions
            logger.warning(f"Standard init failed: {e}, trying without extra params")
            self.client = Groq(api_key)
    
    async def transcribe_with_whisper(self, audio_file) -> str:
        """
        Transcribe audio using Whisper Large v3 via Groq
        
        Args:
            audio_file: Audio file in supported format (webm, wav, mp3, etc.)
            
        Returns:
            str: Transcribed text
        """
        try:
            logger.info("Starting Whisper transcription via Groq")
            
            # Groq's Whisper API
            transcription = self.client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3",
                response_format="text"
            )
            
            logger.info(f"Transcription completed: {len(transcription)} characters")
            return transcription
            
        except Exception as e:
            logger.error(f"Whisper transcription failed: {str(e)}")
            raise Exception(f"Transcription failed: {str(e)}")
    
    async def analyze_with_llama(self, transcript: str, topic: str) -> Dict[str, Any]:
        """
        Analyze transcript using LLaMA 3.3 70B for grammar and vocabulary
        
        Args:
            transcript: Text to analyze
            topic: Speaking topic for context
            
        Returns:
            Dict containing analysis results
        """
        try:
            logger.info("Starting LLaMA 3.3 70B analysis via Groq")
            
            # Construct the analysis prompt
            prompt = self._build_analysis_prompt(transcript, topic)
            
            # Call LLaMA via Groq
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert English language teacher providing detailed feedback for CBSE students. Provide structured JSON responses."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            # Parse the response
            result = self._parse_llama_response(response.choices[0].message.content)
            logger.info("LLaMA analysis completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"LLaMA analysis failed: {str(e)}")
            raise Exception(f"Analysis failed: {str(e)}")
    
    def _build_analysis_prompt(self, transcript: str, topic: str) -> str:
        """Build the analysis prompt for LLaMA"""
        return f"""
Analyze this English speech transcript from a CBSE student speaking about "{topic}":

Transcript: "{transcript}"

Provide a comprehensive analysis in JSON format with the following structure:
{{
    "grammar_score": <score 0-100>,
    "grammar_errors": [
        {{
            "error": "<exact text with error>",
            "correction": "<corrected version>",
            "explanation": "<brief explanation of the grammar rule>"
        }}
    ],
    "vocabulary_score": <score 0-100>,
    "vocabulary_feedback": "<overall vocabulary assessment>",
    "vocabulary_suggestions": [
        {{
            "original": "<simple word/phrase used>",
            "enhanced": "<better alternative>",
            "explanation": "<why this is better>"
        }}
    ],
    "fluency_score": <score 0-100>,
    "fluency_feedback": "<assessment of fluency and natural flow>",
    "coherence_score": <score 0-100>,
    "coherence_feedback": "<assessment of logical structure>",
    "relevance_feedback": "<how well the speech addresses the topic>",
    "positive_highlights": [
        "<specific things done well>"
    ],
    "improvement_areas": [
        "<specific areas to work on>"
    ],
    "rewritten_sample": "<provide a corrected and enhanced version of one key sentence from the transcript>"
}}

Focus on:
1. Grammar accuracy and common errors for Indian English learners
2. Vocabulary appropriateness for CBSE level
3. Sentence structure and coherence
4. Practical, actionable feedback

Be encouraging but specific about areas for improvement.
"""
    
    def _parse_llama_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLaMA response, handling both JSON and text formats"""
        try:
            # Try to parse as JSON first
            # Remove any markdown code blocks if present
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            
            return json.loads(cleaned_text.strip())
            
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLaMA response as JSON, returning structured fallback")
            # Fallback structure if JSON parsing fails
            return {
                "grammar_score": 70,
                "grammar_errors": [],
                "vocabulary_score": 70,
                "vocabulary_feedback": "Analysis in progress",
                "vocabulary_suggestions": [],
                "fluency_score": 70,
                "fluency_feedback": response_text[:500],
                "coherence_score": 70,
                "coherence_feedback": "See detailed feedback",
                "relevance_feedback": "Topic addressed",
                "positive_highlights": ["Clear speech attempted"],
                "improvement_areas": ["Continue practicing"],
                "rewritten_sample": "",
                "raw_response": response_text
            }
    
    async def test_connection(self) -> bool:
        """Test if Groq API connection is working"""
        try:
            # Simple test with a minimal completion
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "user", "content": "Say 'Connection successful' if you can read this."}
                ],
                max_tokens=20
            )
            
            result = "successful" in response.choices[0].message.content.lower()
            logger.info(f"Groq connection test: {'Passed' if result else 'Failed'}")
            return result
            
        except Exception as e:
            logger.error(f"Groq connection test failed: {str(e)}")
            return False


# Test functions for verification
async def test_groq_service():
    """Test function to verify Groq service is working"""
    try:
        service = GroqService()
        
        # Test connection
        print("Testing Groq connection...")
        connected = await service.test_connection()
        print(f"Connection test: {'✓ Passed' if connected else '✗ Failed'}")
        
        # Test LLaMA with sample text
        if connected:
            print("\nTesting LLaMA analysis...")
            sample_transcript = "Today I want to talk about climate change. It is very important issue for our planet. We need to take action immediate to save environment."
            sample_topic = "Environmental Conservation"
            
            result = await service.analyze_with_llama(sample_transcript, sample_topic)
            print(f"Analysis completed. Grammar score: {result.get('grammar_score', 'N/A')}")
            print(f"Found {len(result.get('grammar_errors', []))} grammar errors")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # For testing purposes
    import asyncio
    asyncio.run(test_groq_service())