#!/usr/bin/env python
"""Debug script to test Groq meal plan generation and see raw response."""

import requests
import json
from constants import GROQ_API_KEY, EXAMPLE_MEAL_STRUCTURE

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def test_meal_generation():
    """Test meal plan generation and show raw response."""
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY not found")
        return
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "user",
                "content": (
                    f"You are a nutritionist. Generate a 7-day meal plan for 2000 kcal/day.\n\n"
                    f"CRITICAL: Return ONLY valid JSON (no extra text).\n"
                    f"Use this exact structure:\n"
                    f"{EXAMPLE_MEAL_STRUCTURE}\n\n"
                    f"Requirements:\n"
                    f"- Use common foods\n"
                    f"- Include breakfast, lunch, dinner for 7 days (day1 through day7)\n"
                    f"- All nutrition values must be numbers only (no units)\n"
                    f"- Return ONLY the JSON, nothing else"
                )
            }
        ],
        "temperature": 0.6,
        "max_tokens": 2000
    }
    
    print("Sending request to Groq API...")
    print(f"Model: {payload['model']}")
    print("-" * 60)
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return
        
        result = response.json()
        raw_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        print("\n✅ RAW RESPONSE FROM GROQ:")
        print("-" * 60)
        print(raw_text)
        print("-" * 60)
        
        # Try to parse JSON
        print("\n🔍 PARSING ATTEMPTS:")
        
        # Check if it starts with {
        if raw_text.strip().startswith('{'):
            print("✓ Starts with {")
            try:
                start = raw_text.find('{')
                end = raw_text.rfind('}')
                json_str = raw_text[start:end+1]
                data = json.loads(json_str)
                print(f"✓ Valid JSON parsed! Structure: {list(data.keys())}")
                if "meal_plan" in data:
                    print(f"✓ Contains 'meal_plan' key with {len(data['meal_plan'])} days")
            except json.JSONDecodeError as e:
                print(f"✗ JSON parsing failed: {e}")
        else:
            print("✗ Does NOT start with {")
            print(f"First 100 chars: {raw_text[:100]}")
        
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_meal_generation()
