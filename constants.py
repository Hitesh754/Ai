import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables for local development
load_dotenv()


def _clean_secret(value):
  """Normalize secret/env values by trimming whitespace and optional quotes."""
  if value is None:
    return None
  value = str(value).strip().strip('"').strip("'").strip()
  return value or None


GOOGLE_API_KEY_SOURCE = "missing"
USDA_API_KEY_SOURCE = "missing"

# API Keys - prioritize Streamlit secrets for deployment, fall back to env vars for local
try:
  google_secret_lc = _clean_secret(st.secrets.get("google_api_key"))
  google_secret_uc = _clean_secret(st.secrets.get("GOOGLE_API_KEY"))
  google_env_lc = _clean_secret(os.getenv("google_api_key"))
  google_env_uc = _clean_secret(os.getenv("GOOGLE_API_KEY"))

  usda_secret_lc = _clean_secret(st.secrets.get("usda_api_key"))
  usda_secret_uc = _clean_secret(st.secrets.get("USDA_API_KEY"))
  usda_env_lc = _clean_secret(os.getenv("usda_api_key"))
  usda_env_uc = _clean_secret(os.getenv("USDA_API_KEY"))

  if google_secret_lc:
    GOOGLE_API_KEY = google_secret_lc
    GOOGLE_API_KEY_SOURCE = "streamlit:google_api_key"
  elif google_secret_uc:
    GOOGLE_API_KEY = google_secret_uc
    GOOGLE_API_KEY_SOURCE = "streamlit:GOOGLE_API_KEY"
  elif google_env_lc:
    GOOGLE_API_KEY = google_env_lc
    GOOGLE_API_KEY_SOURCE = "env:google_api_key"
  else:
    GOOGLE_API_KEY = google_env_uc
    if GOOGLE_API_KEY:
      GOOGLE_API_KEY_SOURCE = "env:GOOGLE_API_KEY"

  if usda_secret_lc:
    USDA_API_KEY = usda_secret_lc
    USDA_API_KEY_SOURCE = "streamlit:usda_api_key"
  elif usda_secret_uc:
    USDA_API_KEY = usda_secret_uc
    USDA_API_KEY_SOURCE = "streamlit:USDA_API_KEY"
  elif usda_env_lc:
    USDA_API_KEY = usda_env_lc
    USDA_API_KEY_SOURCE = "env:usda_api_key"
  else:
    USDA_API_KEY = usda_env_uc
    if USDA_API_KEY:
      USDA_API_KEY_SOURCE = "env:USDA_API_KEY"
except:
    # Fallback for local development when streamlit secrets are not available
  GOOGLE_API_KEY = _clean_secret(os.getenv("google_api_key")) or _clean_secret(os.getenv("GOOGLE_API_KEY"))
  USDA_API_KEY = _clean_secret(os.getenv("usda_api_key")) or _clean_secret(os.getenv("USDA_API_KEY"))
  if GOOGLE_API_KEY:
    GOOGLE_API_KEY_SOURCE = "env:fallback"
  if USDA_API_KEY:
    USDA_API_KEY_SOURCE = "env:fallback"

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