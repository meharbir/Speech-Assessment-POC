#!/usr/bin/env python3
"""
Test script to verify Groq service is working correctly
Run this after adding your GROQ_API_KEY to .env file
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


async def main():
    """Test Groq service functionality"""
    print("=" * 50)
    print("GROQ SERVICE TEST")
    print("=" * 50)
    
    # Check if API key is set
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "YOUR_GROQ_API_KEY_HERE":
        print("[ERROR] Please add your GROQ_API_KEY to the .env file")
        print("   Replace 'YOUR_GROQ_API_KEY_HERE' with your actual key")
        return False
    
    print(f"[OK] API Key found: {api_key[:10]}...")
    
    try:
        # Initialize service
        print("\n1. Initializing Groq Service...")
        service = GroqService()
        print("[OK] Service initialized successfully")
        
        # Test connection
        print("\n2. Testing API Connection...")
        connected = await service.test_connection()
        if connected:
            print("[OK] Successfully connected to Groq API")
        else:
            print("[FAILED] Failed to connect to Groq API")
            return False
        
        # Test LLaMA analysis
        print("\n3. Testing LLaMA 3.3 70B Analysis...")
        sample_transcript = """
        Today I want to talk about importance of education. 
        Education are very important for everyone life. 
        It help us to get good job and make better future.
        We should always respect our teacher and study hard.
        """
        sample_topic = "Importance of Education"
        
        result = await service.analyze_with_llama(sample_transcript, sample_topic)
        
        print("[OK] Analysis completed successfully!")
        print(f"\nResults:")
        print(f"  - Grammar Score: {result.get('grammar_score', 'N/A')}/100")
        print(f"  - Vocabulary Score: {result.get('vocabulary_score', 'N/A')}/100")
        print(f"  - Grammar Errors Found: {len(result.get('grammar_errors', []))}")
        
        if result.get('grammar_errors'):
            print(f"\n  Sample Grammar Error:")
            error = result['grammar_errors'][0]
            print(f"    Original: {error.get('error', 'N/A')}")
            print(f"    Correction: {error.get('correction', 'N/A')}")
            print(f"    Explanation: {error.get('explanation', 'N/A')}")
        
        # Note about Whisper testing
        print("\n4. Whisper Transcription Test")
        print("   [NOTE] Whisper requires an actual audio file to test")
        print("   This will be tested when we implement the full endpoint")
        
        print("\n" + "=" * 50)
        print("[SUCCESS] ALL TESTS PASSED - Groq service is ready!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        print("\nPossible issues:")
        print("  1. Invalid API key")
        print("  2. Rate limit exceeded")
        print("  3. Network connection issues")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)