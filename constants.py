import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables for local development
load_dotenv()

# API Keys - prioritize Streamlit secrets for deployment, fall back to env vars for local
try:
    GOOGLE_API_KEY = st.secrets.get("google_api_key") or os.getenv("google_api_key")
    USDA_API_KEY = st.secrets.get("usda_api_key") or os.getenv("usda_api_key")
except:
    # Fallback for local development when streamlit secrets are not available
    GOOGLE_API_KEY = os.getenv("google_api_key")
    USDA_API_KEY = os.getenv("usda_api_key")

USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

EXAMPLE_MEAL_STRUCTURE = '''{
  "meal_plan": {
    "day1": {
      "breakfast": {
        "dish_name": "Example Dish",
        "portion_grams": 150,
        "nutrition": {
          "calories": 300,
          "protein": 20,
          "carbs": 35,
          "fat": 10
        },
        "data_source": "USDA"  
      }
    }
  }
}'''