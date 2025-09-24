import streamlit as st

# API Keys from Streamlit secrets (replace with your values if local)
GOOGLE_API_KEY = st.secrets.get("google_api_key") or "AIzaSyCB85c3lVwkdLwZg9L14XGIplDZTeTzOqA"
USDA_API_KEY = st.secrets.get("usda_api_key") or "0bD1SYsk0t5TOmgteyURcMp4XVSb3jgmMTGsU2to"

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

