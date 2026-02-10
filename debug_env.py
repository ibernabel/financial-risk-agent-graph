#!/usr/bin/env python3
"""
Debug script to check environment variable loading.
"""

from dotenv import load_dotenv
import os
from app.core.config import settings
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


print("="*80)
print("Environment Variable Debug")
print("="*80)

# Check if .env file exists
env_file = Path(".env")
print(f"\n1. .env file exists: {env_file.exists()}")
print(f"   Path: {env_file.absolute()}")

# Try loading .env manually
print(f"\n2. Manually loading .env with python-dotenv...")
load_dotenv()

# Check environment variable
print(f"\n3. Checking OPENAI_API_KEY in os.environ:")
openai_key_env = os.environ.get("OPENAI_API_KEY", "NOT FOUND")
if openai_key_env != "NOT FOUND":
    masked = f"{openai_key_env[:10]}...{openai_key_env[-4:]}"
    print(f"   ✅ Found in os.environ: {masked}")
else:
    print(f"   ❌ NOT FOUND in os.environ")

# Check Pydantic Settings
print(f"\n4. Checking settings.llm.openai_api_key:")
settings_key = settings.llm.openai_api_key
if settings_key:
    masked = f"{settings_key[:10]}...{settings_key[-4:]}"
    print(f"   ✅ Found in Pydantic Settings: {masked}")
else:
    print(f"   ❌ NOT FOUND in Pydantic Settings (empty string)")

# Display other LLM settings
print(f"\n5. Other LLM Settings:")
print(f"   OCR Model: {settings.llm.ocr_llm_model}")
print(f"   Temperature: {settings.llm.ocr_temperature}")
print(f"   Max Tokens: {settings.llm.ocr_max_tokens}")

print("\n" + "="*80)
