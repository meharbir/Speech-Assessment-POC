#!/usr/bin/env python3
"""
Quick test for Groq JSON parsing improvements
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from groq_service import GroqService

async def test_json_parsing():
    """Test the improved JSON parsing"""
    print("=" * 50)
    print("TESTING GROQ JSON PARSING IMPROVEMENTS")
    print("=" * 50)
    
    # Check if API key is set
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("[ERROR] Please add your GROQ_API_KEY to the .env file")
        return False
    
    print(f"[OK] API Key found: {api_key[:10]}...")
    
    try:
        # Initialize service
        print("\n1. Initializing Groq Service...")
        service = GroqService()
        print("[OK] Service initialized successfully")
        
        # Test with a simple transcript that often causes JSON issues
        print("\n2. Testing JSON parsing with problematic transcript...")
        
        sample_transcript = """
        Hello everyone, I'm going to talk about my favorite hobby. 
        My hobby is reading books - especially fiction and "adventure stories".
        It's really amazing how books can transport you to different worlds.
        I think everyone should have a hobby that they're passionate about.
        """
        sample_topic = "My Favorite Hobby"
        
        print("   Sending to Groq LLaMA for analysis...")
        result = await service.analyze_with_llama(sample_transcript, sample_topic)
        
        # Check if parsing was successful
        if result.get("parse_error"):
            print(f"[WARNING] JSON parsing failed, using fallback")
            print(f"   Raw response preview: {result.get('raw_response', 'N/A')[:200]}...")
            return False
        else:
            print("[SUCCESS] JSON parsed successfully!")
            print(f"   Grammar Score: {result.get('grammar_score', 'N/A')}/100")
            print(f"   Vocabulary Score: {result.get('vocabulary_score', 'N/A')}/100")
            print(f"   Fluency Score: {result.get('fluency_score', 'N/A')}/100")
            print(f"   Grammar Errors Found: {len(result.get('grammar_errors', []))}")
            
            # Show first vocabulary suggestion if available
            vocab_suggestions = result.get('vocabulary_suggestions', [])
            if vocab_suggestions:
                first_suggestion = vocab_suggestions[0]
                print(f"   Sample Vocab Suggestion: {first_suggestion.get('original', 'N/A')} -> {first_suggestion.get('enhanced', 'N/A')}")
            
            return True
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Groq JSON parsing improvements...")
    success = asyncio.run(test_json_parsing())
    
    if success:
        print("\n" + "=" * 50)
        print("[SUCCESS] JSON parsing improvements working!")
        print("The hybrid endpoint should now work properly.")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("[ISSUE] JSON parsing still has problems.")
        print("Check the logs for the actual LLaMA response format.")
        print("=" * 50)
    
    sys.exit(0 if success else 1)