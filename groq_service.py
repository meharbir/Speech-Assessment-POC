import os
import json
import re
from groq import Groq
from typing import Dict, Any, Optional
import logging
from rubrics import CBSE_ASL_DETAILED_RUBRIC

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
            
            # Call LLaMA via Groq with strict JSON formatting instructions
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a JSON generator. Output ONLY valid JSON. No text before or after. No comments. No explanations. Start with { and end with }."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.0,  # Fully deterministic
                max_tokens=2500,  # Increased for longer responses
                response_format={"type": "json_object"} if hasattr(self.client, 'response_format') else None
            )
            
            # Parse the response
            result = self._parse_llama_response(response.choices[0].message.content)
            logger.info("LLaMA analysis completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"LLaMA analysis failed: {str(e)}")
            raise Exception(f"Analysis failed: {str(e)}")
    
    def _build_analysis_prompt(self, transcript: str, topic: str) -> str:
        """Build the analysis prompt for LLaMA using the same rubric as OpenAI"""
        return f"""
You are an expert AI English Tutor for a student in India. Your task is to provide a comprehensive evaluation of their impromptu speech based on the official CBSE ASL rubric. Your final scores MUST be converted to a 100-point scale (e.g., a rubric score of 4/5 is 80/100).

--- OFFICIAL CBSE ASL DETAILED RUBRIC ---
{CBSE_ASL_DETAILED_RUBRIC}
--- END OF RUBRIC ---

The student was asked to speak on the topic: "{topic}".
The student's transcript is: "{transcript}"

You MUST evaluate the transcript strictly against the provided detailed rubric. Your feedback and scores must directly reflect the criteria outlined. Provide at least 3-5 vocabulary enhancement suggestions with specific words/phrases from the transcript.

CRITICAL INSTRUCTIONS:
1. Output ONLY the JSON object below
2. No text before or after the JSON
3. Use double quotes for all strings
4. No trailing commas
5. Escape any quotes inside string values with \"
6. Ensure all brackets and braces are properly closed

Output exactly this structure:
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

Start your response with {{ and end with }}. Nothing else.
"""
    
    def _parse_llama_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLaMA response, handling both JSON and text formats"""
        try:
            # Log the raw response for debugging
            logger.info(f"Raw LLaMA response (first 500 chars): {response_text[:500]}")
            
            # Aggressive JSON extraction and cleaning
            cleaned_text = response_text.strip()
            
            # Try to find JSON boundaries
            json_start = cleaned_text.find('{')
            json_end = cleaned_text.rfind('}')
            
            if json_start != -1 and json_end != -1:
                json_str = cleaned_text[json_start:json_end+1]
                
                # Remove any markdown artifacts
                json_str = json_str.replace('```json', '').replace('```', '')
                
                # Fix common JSON issues
                json_str = self._fix_common_json_issues(json_str)
                
                # Attempt to parse
                parsed = json.loads(json_str)
                
                # Validate required fields exist
                required_fields = ['grammar_score', 'vocabulary_score', 'fluency_score', 'relevance_score', 'pronunciation_score']
                if all(field in parsed for field in required_fields):
                    logger.info("Successfully parsed LLaMA JSON response")
                    return parsed
                else:
                    logger.warning(f"Missing required fields in LLaMA response: {[f for f in required_fields if f not in parsed]}")
            
            # If parsing fails, log the actual response for debugging
            logger.warning(f"LLaMA response not valid JSON. Full response: {response_text}")
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error at line {getattr(e, 'lineno', '?')} col {getattr(e, 'colno', '?')}: {e}")
            # Log the exact character causing problems
            if hasattr(e, 'pos') and e.pos < len(json_str):
                problem_char = json_str[e.pos] if e.pos < len(json_str) else 'EOF'
                if problem_char != 'EOF':
                    logger.error(f"Problem character at position {e.pos}: '{problem_char}' (ASCII: {ord(problem_char)})")
            logger.error(f"Problematic JSON: {response_text}")
        except Exception as e:
            logger.error(f"Unexpected parsing error: {e}")
        
        # Return comprehensive fallback matching OpenAI structure
        return {
            "relevance_score": 75,
            "relevance_feedback": "Analysis processing - topic addressed appropriately",
            "fluency_score": 75,
            "fluency_feedback": "Analysis in progress",
            "pronunciation_score": 75,
            "pronunciation_feedback": "Analysis in progress",
            "grammar_score": 75,
            "grammar_errors": [],
            "vocabulary_score": 75,
            "vocabulary_feedback": "Analysis processing - see raw response",
            "vocabulary_suggestions": [],
            "detailed_fluency_coherence_analysis": "Analysis processing - comprehensive review in progress",
            "positive_highlights": ["Speech recorded successfully"],
            "rewritten_sample": "",
            "parse_error": True,
            "raw_response": response_text[:1000]  # Include for debugging
        }
    
    def _fix_common_json_issues(self, json_str: str) -> str:
        """Fix common JSON formatting issues from LLaMA responses"""
        # Remove trailing commas before closing braces/brackets
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Strip all control characters except newline and tab
        json_str = ''.join(ch for ch in json_str if ord(ch) >= 32 or ch in '\n\t')
        
        # NEW: Handle newlines properly in JSON strings
        # Split into lines but preserve the structure
        import json
        try:
            # Try to parse as-is first
            test_parse = json.loads(json_str)
            # If it works, we're done with newline handling
        except:
            # If parsing fails, escape newlines in string values only
            # This is a safer approach - replace newlines with spaces
            json_str = json_str.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        
        # NEW: Remove any zero-width characters and other invisible Unicode
        json_str = re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff]', '', json_str)
        
        # Remove any text before the first { or after the last }
        first_brace = json_str.find('{')
        last_brace = json_str.rfind('}')
        if first_brace != -1 and last_brace != -1:
            json_str = json_str[first_brace:last_brace+1]
        
        # Final cleanup - ensure no trailing commas before closing brackets
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        return json_str
    
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