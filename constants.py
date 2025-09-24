import os
from dotenv import load_dotenv
import streamlit as st

# Load environment variables from .env file
GOOGLE_API_KEY = st.secrets.get("google_api_key")
USDA_API_KEY = st.secrets.get("usda_api_key")
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

