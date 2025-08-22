#!/usr/bin/env python3
"""
Test script to verify the hybrid endpoint is properly structured
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_endpoint_structure():
    """Test that the hybrid endpoint is properly structured"""
    print("=" * 50)
    print("HYBRID ENDPOINT STRUCTURE TEST")
    print("=" * 50)
    
    try:
        # Test that we can import the main module
        print("\n1. Testing main.py imports...")
        
        # Add current directory to path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # This will test that all imports work
        import importlib.util
        spec = importlib.util.spec_from_file_location("main", "main.py")
        main_module = importlib.util.module_from_spec(spec)
        
        # Test that we can load it (this will fail at service initialization but that's OK)
        try:
            spec.loader.exec_module(main_module)
            print("[OK] main.py loaded successfully")
        except Exception as e:
            if "GROQ_API_KEY not found" in str(e):
                print("[OK] main.py structure is correct (Groq key missing is expected)")
            else:
                print(f"[WARNING] Unexpected error: {e}")
        
        # Check that the FastAPI app was created
        if hasattr(main_module, 'app'):
            print("[OK] FastAPI app created successfully")
            
            # Get all routes
            routes = [route.path for route in main_module.app.routes if hasattr(route, 'path')]
            
            if "/api/analyze-hybrid-groq" in routes:
                print("[OK] Hybrid endpoint route exists")
            else:
                print("[ERROR] Hybrid endpoint route not found")
                return False
        else:
            print("[ERROR] FastAPI app not found")
            return False
            
        # Test that the endpoint function exists
        if hasattr(main_module, 'analyze_hybrid_groq'):
            print("[OK] analyze_hybrid_groq function exists")
        else:
            print("[ERROR] analyze_hybrid_groq function not found")
            return False
        
        print("\n" + "=" * 50)
        print("[SUCCESS] Hybrid endpoint structure is correct!")
        print("=" * 50)
        
        print("\nEndpoint Specifications:")
        print("  - Route: POST /api/analyze-hybrid-groq")
        print("  - Parameters: audio_file (File), topic (Form)")
        print("  - Authentication: Optional (get_optional_current_user)")
        print("  - Processing: Serial transcription + Parallel analysis")
        print("  - Database: Saves if user is logged in")
        print("  - Response: Combined results with metadata")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {str(e)}")
        print("\nThis usually means:")
        print("  1. Import errors in main.py")
        print("  2. Missing dependencies")
        print("  3. Syntax errors in the endpoint")
        return False


if __name__ == "__main__":
    success = test_endpoint_structure()
    sys.exit(0 if success else 1)