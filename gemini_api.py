# gemini_api_fixed.py
import requests
import base64
import json
import re
import logging
import pandas as pd
import streamlit as st  # Required because st.error/warning are used directly here

from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from constants import GOOGLE_API_KEY, USDA_API_KEY, USDA_BASE_URL, EXAMPLE_MEAL_STRUCTURE

# Configure logger for this module
log = logging.getLogger(__name__)

if not GOOGLE_API_KEY:
    st.error("❌ Google API key ('google_api_key') not found in .env file")
    st.stop()

if not USDA_API_KEY:
    st.warning("⚠️ USDA API key ('usda_api_key') not found in .env file. Enhanced grounding will be limited.")

def validate_meal_plan_nutrition(meal_plan: dict) -> dict:
    """Cross-check generated nutrition data with USDA database"""
    validation_results = {
        "total_dishes": 0,
        "usda_verified": 0,
        "calorie_discrepancies": [],
        "macro_discrepancies": []
    }
    
    for day, meals in meal_plan.get("meal_plan", {}).items():
        for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
            meal = meals.get(meal_type, {})
            if not meal.get("dish_name"):
                continue
            
            validation_results["total_dishes"] += 1
            
            # Get USDA data
            usda_data = fetch_nutrition_data_from_usda(meal["dish_name"])
            if not usda_data:
                continue
                
            validation_results["usda_verified"] += 1
            
            # Compare values
            generated = meal.get("nutrition", {})
            discrepancies = {}
            
            for key in ["calories", "protein", "carbs", "fat"]:
                gen_val = generated.get(key, 0)
                usda_val = usda_data.get(key, 0)
                
                if usda_val > 0 and abs(gen_val - usda_val)/usda_val > 0.15:  # 15% threshold
                    discrepancies[key] = {
                        "generated": gen_val,
                        "usda": usda_val,
                        "variance": round((gen_val - usda_val)/usda_val * 100, 1)
                    }
            
            if discrepancies:
                validation_results["calorie_discrepancies"].append({
                    "dish": meal["dish_name"],
                    **discrepancies
                })
    
    return validation_results

def fetch_nutrition_data_from_usda(food_name: str) -> dict:
    try:
        params = {
            "api_key": USDA_API_KEY,
            "query": food_name,
            "pageSize": 3,
            "dataType": ["Survey (FNDDS)"]
        }
        response = requests.get(USDA_BASE_URL, params=params, timeout=15)
        response.raise_for_status()
        
        best_match = None
        best_score = 0
        
        for food in response.json().get("foods", []):
            score = fuzz.ratio(food_name.lower(), food["description"].lower())
            if score > best_score:
                best_match = food
                best_score = score
                
        if best_score < 65:
            return None
            
        nutrients = {
            "calories": get_nutrient_value(best_match, "Energy"),
            "protein": get_nutrient_value(best_match, "Protein"),
            "carbs": get_nutrient_value(best_match, "Carbohydrate, by difference"),
            "fat": get_nutrient_value(best_match, "Total lipid (fat)")
        }
        
        if all(v > 0 for v in nutrients.values()):
            return nutrients
            
    except Exception as e:
        log.error(f"USDA fetch error: {str(e)}")
        return None

def get_nutrient_value(food_data: dict, nutrient_name: str) -> float:
    return next(
        (n["value"] for n in food_data.get("foodNutrients", []) 
         if n.get("nutrientName") == nutrient_name and n.get("unitName") == "kcal"),
        0.0
    )

def analyze_image_with_rest(api_key: str, image_bytes: bytes, language: str = "English"):
    log.info(f"Entering analyze_image_with_rest for language: {language}")
    if not api_key:
        log.error("API key is missing for analyze_image_with_rest.")
        st.error("Configuration error: API Key not provided.")
        return None
    if not image_bytes:
        log.warning("No image bytes provided for analysis.")
        st.warning("No image bytes provided for analysis.")
        return None

    try:
        img_base64 = base64.b64encode(image_bytes).decode("utf-8")
        api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GOOGLE_API_KEY}"
        }

        prompt = (
            f"Analyze this food image precisely. Respond ONLY with a valid JSON object "
            f"(no extra text or markdown formatting) like this: "
            f"{{\"food\": \"Best guess name\", \"estimated_calories\": <number>, "
            f"\"macros\": {{\"protein\": <number>, \"carbs\": <number>, \"fat\": <number>}}, "
            f"\"portion_grams\": <number>}}. "
            f"Respond in {language} for the 'food' name if possible, keep keys in English."
        )

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_base64}}
                ]
            }]
        }

        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        log.info(f"Vision API Status Code: {response.status_code}")
        log.info(f"Vision API Response Text (first 500): {response.text[:500]}")
        response.raise_for_status()
        result_json = response.json()

        if not result_json.get("candidates"):
            log.error("Vision Error: No 'candidates' found in API response.")
            st.error("❌ Image Analysis Error: No 'candidates' found in API response.")
            return None

        text_result = result_json["candidates"][0]["content"]["parts"][0]["text"]

        match = re.search(r"```json\s*(\{.*?\})\s*```", text_result, re.DOTALL | re.IGNORECASE)
        if not match:
            match = re.search(r"(\{.*?\})", text_result.strip(), re.DOTALL)

        if not match:
            log.error("Vision Error: Could not parse/find JSON block in response text.")
            st.error("⚠️ Image Analysis Error: Could not find expected JSON data in AI response.")
            return None

        json_str = match.group(1)
        analysis_data = json.loads(json_str)

        food_name = analysis_data.get("food")
        if food_name:
            usda_nutrition = fetch_nutrition_data_from_usda(food_name)
            if usda_nutrition:
                portion_grams = analysis_data.get("portion_grams", 100)
                analysis_data["verified_nutrition"] = {
                    "calories": (usda_nutrition["calories"] / 100) * portion_grams,
                    "protein": (usda_nutrition["protein"] / 100) * portion_grams,
                    "carbs": (usda_nutrition["carbs"] / 100) * portion_grams,
                    "fat": (usda_nutrition["fat"] / 100) * portion_grams
                }
                analysis_data["data_source"] = "USDA"
            else:
                analysis_data["data_source"] = "AI Estimate"

        return analysis_data

    except requests.exceptions.RequestException as e:
        log.error(f"API Request Error (Vision): {e}")
        st.error(f"❌ Network Error: Failed to connect to Image Analysis service ({e})")
        return None
    except Exception as e:
        log.exception("Unexpected error during image analysis.")
        st.error(f"❌ An unexpected error occurred during image analysis: {e}")
        return None
    finally:
        log.info("Exiting analyze_image_with_rest")

# --- GENERATE MEAL PLAN ---
def generate_meal_plan_with_rest(api_key: str, calorie_target: int, preferences: dict, language: str = "English"):
    log.info(f"Entering generate_meal_plan_with_rest for {calorie_target} kcal, lang: {language}")
    if not api_key:
        log.error("API key is missing for generate_meal_plan_with_rest.")
        st.error("Configuration error: API Key not provided.")
        return None
    if not calorie_target or not preferences:
        log.warning("Missing calorie target or preferences for meal plan.")
        return None

    try:
        api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GOOGLE_API_KEY}"
        }

        restrictions_str = ', '.join(preferences.get('restrictions', [])) or 'None'
        favorites_str = preferences.get('favorites', 'Any')
        dislikes_str = preferences.get('dislikes', 'None')

        meal_prompt = (
            f"You are a nutritionist AI assistant. The user needs **{calorie_target} kcal/day**.\n"
            f"Generate a JSON meal plan for 7 days ONLY.\n\n"
            f"User Preferences:\n"
            f"- Goal: {preferences.get('goal', 'Maintain Weight')}\n"
            f"- Diet/Restrictions: {restrictions_str}\n"
            f"- Favorite Foods: {favorites_str}\n"
            f"- Disliked Foods: {dislikes_str}\n\n"
            f"Critical Requirements:\n"
            f"1. Use COMMON, WELL-KNOWN FOOD ITEMS from standard nutritional databases\n"
            f"2. For each meal's nutrition data:\n"
            f"   a) First check USDA FoodData Central database values using its API\n"
            f"   b) Clearly note if values are estimates with 'estimated_' prefix\n"
            f"3. Format nutrition values as NUMBERS ONLY (no units)\n"
            f"4. Ensure portion sizes use STANDARD METRIC measurements (grams)\n"
            f"5. Include a 'data_source': 'USDA' field for each meal to indicate the source of nutrition data.\n"
            f"**6. For each day, include 1-2 realistic snack options. A typical snack should be between 100-300 kcal.**\n"
            f"Response MUST be valid JSON with 'meal_plan' key following this structure:\n"
            f"{EXAMPLE_MEAL_STRUCTURE}"
        )

        payload = {
            "contents": [{"role": "user", "parts": [{"text": meal_prompt}]}],
            "generationConfig": {"temperature": 0.6}
        }

        response = requests.post(api_url, headers=headers, json=payload, timeout=180)
        log.info(f"Meal Plan API Status Code: {response.status_code}")
        log.info(f"Meal Plan API Response Text (first 500): {response.text[:500]}")
        response.raise_for_status()
        result_json = response.json()

        text_result = result_json["candidates"][0]["content"]["parts"][0]["text"]

        match = re.search(r"```json\s*(\{.*?\})\s*```", text_result, re.DOTALL | re.IGNORECASE)
        if not match:
            if text_result.strip().startswith('{') and text_result.strip().endswith('}'):
                match = re.search(r"(\{.*?\})", text_result.strip(), re.DOTALL)

        if not match:
            log.error("Could not parse/find JSON block within the meal plan text response.")
            st.error("⚠️ Meal Plan Error: Could not find expected JSON data in AI response.")
            return None

        json_str = match.group(1)
        meal_data = json.loads(json_str)
        return meal_data.get("meal_plan")

    except requests.exceptions.RequestException as e:
        log.error(f"API Request Error (Meal Plan): {e}")
        st.error(f"❌ Network Error: Failed to connect to Meal Plan service ({e})")
        return None
    except Exception as e:
        log.exception("Unexpected error during meal plan generation.")
        st.error(f"❌ An unexpected error occurred during meal plan generation: {e}")
        return None
    finally:
        log.info("Exiting generate_meal_plan_with_rest")

# --- GENERATE GROCERY LIST ---
def generate_grocery_list_with_rest(api_key: str, meal_plan_dict: dict, language: str = "English"):
    log.info("Entering generate_grocery_list_with_rest")
    if not api_key:
        log.error("API key is missing for generate_grocery_list_with_rest.")
        st.error("Configuration error: API Key not provided.")
        return None
    if not meal_plan_dict or not isinstance(meal_plan_dict, dict):
        log.warning("Invalid or empty meal_plan_dict provided for grocery list.")
        return None

    all_dishes = []
    for day_key, day_content in meal_plan_dict.items():
        if not isinstance(day_content, dict):
            continue
        for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
            info = day_content.get(meal_type)
            if isinstance(info, dict):
                if "dish_name" in info:
                    all_dishes.append(info["dish_name"])
            elif isinstance(info, list):
                for item in info:
                    if isinstance(item, dict) and "dish_name" in item:
                        all_dishes.append(item["dish_name"])

    if not all_dishes:
        st.warning("No dish names found in the plan to create a grocery list.")
        return None

    unique_dishes = sorted(list(set(filter(None, all_dishes))))
    dishes_text = ", ".join(unique_dishes)

    prompt = f"""Act as a helpful shopping assistant. Based *only* on the following list of meal dishes planned for a week, generate a likely grocery list of ingredients needed.

Dishes Planned:
{dishes_text}

Instructions for Grocery List:
- List necessary ingredients to make these dishes in {language}.
- Combine similar items. Estimate reasonable weekly quantities for one person.
- Group ingredients into logical categories using Markdown H3 headings.
- Exclude: salt, black pepper, water, basic vegetable/canola oil.
- Format the output *only* as a Markdown list with bullet points (*) under category headings.
- Do NOT include introductory or concluding sentences. Just the list.
"""

    try:
        api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GOOGLE_API_KEY}"
        }
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3}
        }

        response = requests.post(api_url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        result_json = response.json()

        grocery_list_text = result_json["candidates"][0]["content"]["parts"][0]["text"]
        grocery_list_text = re.sub(r"^```markdown\s*\n?", "", grocery_list_text, flags=re.IGNORECASE | re.MULTILINE)
        grocery_list_text = re.sub(r"\n?```\s*$", "", grocery_list_text, flags=re.IGNORECASE | re.MULTILINE)
        return grocery_list_text.strip()

    except requests.exceptions.RequestException as e:
        log.error(f"API Request Error (Grocery List): {e}")
        st.error(f"❌ Network Error connecting to AI for grocery list ({e})")
        return None
    except Exception as e:
        log.exception("Unexpected error during grocery list generation.")
        st.error(f"❌ Unexpected error creating grocery list: {e}")
        return None
    finally:
        log.info("Exiting generate_grocery_list_with_rest")
