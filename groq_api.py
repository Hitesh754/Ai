import requests
import base64
import json
import re
import logging
import pandas as pd
import streamlit as st

from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from constants import GROQ_API_KEY, USDA_API_KEY, USDA_BASE_URL, EXAMPLE_MEAL_STRUCTURE

# Configure logger for this module
log = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# List of Groq models in priority order (will automatically fallback if model is decommissioned)
# Updated from https://api.groq.com/openai/v1/models endpoint
GROQ_MODELS = [
    "llama-3.3-70b-versatile",      # Latest, most powerful Llama model
    "llama-3.1-8b-instant",         # Fast, optimized for quick responses
    "openai/gpt-oss-120b",          # High-capacity alternative
    "openai/gpt-oss-20b",           # Mid-range alternative
    "groq/compound",                # Groq's compound model
    "groq/compound-mini"            # Lightweight fallback
]

if not GROQ_API_KEY:
    st.error("❌ Groq API key ('groq_api_key') not found.")
    st.info("Get free API key from: https://console.groq.com/keys")
    st.info("Add it as 'groq_api_key' in Streamlit secrets or .env file.")
    st.stop()

if not USDA_API_KEY:
    st.warning("⚠️ USDA API key ('usda_api_key') not found in .env file. Enhanced grounding will be limited.")


def _call_groq_with_fallback(api_key: str, messages: list, temperature: float, max_tokens: int, models: list = None, feature_name: str = "API"):
    """
    Call Groq API with automatic model fallback.
    Tries each model in sequence until one succeeds.
    Returns (response, used_model) or raises on final failure.
    """
    if models is None:
        models = GROQ_MODELS
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    last_error = None
    
    for model in models:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            log.info(f"Attempting Groq API call with model: {model}")
            response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=180)
            
            # Check if model is decommissioned
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    error_code = error_data.get("error", {}).get("code", "")
                    error_msg = error_data.get("error", {}).get("message", "")
                    
                    if "decommissioned" in error_msg.lower():
                        log.warning(f"Model {model} is decommissioned, trying next fallback...")
                        last_error = error_msg
                        continue
                except Exception:
                    pass
            
            # If we get here and status is not 2xx, raise for error handling
            response.raise_for_status()
            log.info(f"Groq API call succeeded with model: {model}")
            return response, model
            
        except requests.exceptions.RequestException as e:
            log.warning(f"Model {model} failed: {str(e)}, trying next...")
            last_error = str(e)
            continue
    
    # All models failed
    if last_error:
        raise RuntimeError(f"All Groq models exhausted. Last error: {last_error}")
    else:
        raise RuntimeError("Failed to call Groq API with any model")


def _handle_groq_http_error(err: requests.exceptions.HTTPError, feature_name: str) -> None:
    """Show user-friendly, actionable Groq API errors in Streamlit."""
    response = err.response
    status_code = response.status_code if response is not None else None

    message = ""
    raw_text = ""
    if response is not None:
        raw_text = (response.text or "")[:500]
        try:
            payload = response.json()
            message = payload.get("error", {}).get("message", "")
        except Exception:
            message = ""

    lower_message = message.lower()
    if status_code == 429 and ("rate" in lower_message or "limit" in lower_message):
        st.error(
            f"❌ {feature_name} failed: Rate limit reached. Groq free tier has generous limits, please wait a moment and try again."
        )
        st.info("For higher limits, visit: https://console.groq.com")
        return

    if status_code in (401, 403):
        st.error(
            f"❌ {feature_name} failed: Groq API key is invalid or expired. Get a new one from https://console.groq.com/keys"
        )
        return

    if status_code:
        st.error(f"❌ {feature_name} failed with API error {status_code}. Please try again later.")
    else:
        st.error(f"❌ {feature_name} failed due to an API error. Please try again later.")

    if message:
        st.caption(f"API message: {message[:280]}")
    elif raw_text:
        st.caption(f"Raw API error: {raw_text[:280]}")


def test_groq_connection(api_key: str):
    """Return (ok, message) after a minimal Groq API round-trip."""
    if not api_key:
        return False, "API key missing"

    messages = [{"role": "user", "content": "Say: OK"}]
    
    try:
        response, used_model = _call_groq_with_fallback(
            api_key=api_key,
            messages=messages,
            temperature=0,
            max_tokens=10,
            feature_name="connectivity test"
        )
        if response.status_code == 200:
            return True, f"Groq API reachable using {used_model}"
        return False, f"HTTP {response.status_code}"
    except Exception as exc:
        return False, f"Error: {str(exc)[:220]}"



def fetch_nutrition_data_from_usda(food_name: str) -> dict:
    """Fetches nutrition data for a given food name from the USDA FoodData Central API."""
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
    """Safe nutrient value extraction"""
    return next(
        (n["value"] for n in food_data.get("foodNutrients", []) 
         if n.get("nutrientName") == nutrient_name and n.get("unitName") == "kcal"),
        0.0
    )


def generate_meal_plan_with_rest(api_key: str, calorie_target: int, preferences: dict, language: str = "English"):
    """
    Generates a 7-day meal plan dictionary using Groq API.
    Returns a dictionary { "day1": {...}, ... } or None on failure.
    """
    log.info(f"Entering generate_meal_plan_with_rest for {calorie_target} kcal, lang: {language}")
    if not api_key:
        log.error("API key is missing for generate_meal_plan_with_rest.")
        st.error("Configuration error: API Key not provided.")
        return None
    if not calorie_target or not preferences:
        log.warning("Missing calorie target or preferences for meal plan.")
        return None

    try:
        restrictions_str = ', '.join(preferences.get('restrictions', [])) or 'None'
        favorites_str = preferences.get('favorites', 'Any')
        dislikes_str = preferences.get('dislikes', 'None')

        meal_prompt = (
            f"You are a nutritionist AI assistant. Generate a 7-day meal plan for {calorie_target} kcal/day.\n\n"
            f"User Preferences:\n"
            f"- Goal: {preferences.get('goal', 'Maintain Weight')}\n"
            f"- Diet/Restrictions: {restrictions_str}\n"
            f"- Favorite Foods: {favorites_str}\n"
            f"- Disliked Foods: {dislikes_str}\n\n"
            f"CRITICAL: Return ONLY valid JSON (no extra text before or after).\n"
            f"Use this exact structure:\n"
            f"{EXAMPLE_MEAL_STRUCTURE}\n\n"
            f"Requirements:\n"
            f"- Use common, well-known foods\n"
            f"- Include breakfast, lunch, dinner for 7 days (day1 through day7)\n"
            f"- All nutrition values must be numbers only (no units)\n"
            f"- portion_grams must be realistic\n"
            f"- data_source can be 'USDA' or 'AI'\n"
            f"- Return ONLY the JSON, nothing else"
        )

        log.info("Sending Meal Plan Prompt (first 300 chars):\n%s", meal_prompt[:300] + "...")

        messages = [{"role": "user", "content": meal_prompt}]
        
        log.info("Calling Groq API for meal plan generation with model fallback")
        response, used_model = _call_groq_with_fallback(
            api_key=api_key,
            messages=messages,
            temperature=0.6,
            max_tokens=2000,
            feature_name="meal plan generation"
        )
        log.info(f"Meal Plan API Status Code: {response.status_code}")
        log.info(f"Used model: {used_model}")
        log.info(f"Meal Plan API Response Text (first 500): {response.text[:500]}")

        response.raise_for_status()

        result_json = response.json()
        if not result_json.get("choices"):
            log.error("Meal Plan Error: No 'choices' found in API response JSON.")
            st.error("❌ Meal Plan Error: No 'choices' found in AI response.")
            log.error("Full API Response: %s", result_json)
            return None

        try:
            text_result = result_json["choices"][0]["message"]["content"]
            log.info(f"Meal Plan Extracted Text (first 500): {text_result[:500]}")

            if text_result:
                log_entry = {
                    "timestamp": pd.Timestamp.now(tz='UTC').isoformat(),
                    "function_called": "generate_meal_plan",
                    "input_context": {
                        "calorie_target": calorie_target,
                        "preferences": preferences,
                        "language": language,
                        "api_provider": "groq"
                    },
                    "raw_response_text": text_result
                }
                try:
                    with open("api_log.jsonl", "a", encoding="utf-8") as f:
                        json.dump(log_entry, f)
                        f.write("\n")
                    log.info("Successfully logged meal plan request/response to api_log.jsonl")
                except Exception as log_e:
                    log.error(f"Failed to write to evaluation log file: {log_e}")

        except (KeyError, IndexError, TypeError) as e:
            log.error(f"Meal Plan Error: Could not extract text part: {e}")
            st.error(f"❌ Meal Plan Error: Could not process AI response structure: {e}")
            log.error("Full API Response: %s", result_json)
            return None

        # Parse JSON from the text result - more robust extraction
        json_str = None
        
        # Try 1: Look for ```json```  code block (most common)
        match = re.search(r"```json\s*\n?([\s\S]*?)\n?```", text_result, re.IGNORECASE)
        if match:
            json_str = match.group(1).strip()
        
        # Try 2: Look for ```  code block (no language specified)
        if not json_str:
            match = re.search(r"```\s*\n?([\s\S]*?)\n?```", text_result)
            if match:
                potential_json = match.group(1).strip()
                # Verify it looks like JSON
                if potential_json.startswith('{'):
                    json_str = potential_json
        
        # Try 3: Look for raw JSON (starts with { and ends with })
        if not json_str:
            if text_result.strip().startswith('{'):
                # Find the last } to capture complete JSON
                start_idx = text_result.find('{')
                end_idx = text_result.rfind('}')
                if end_idx > start_idx:
                    json_str = text_result[start_idx:end_idx + 1].strip()

        if not json_str:
            log.error("Could not parse/find JSON block within the meal plan text response.")
            log.error(f"Response preview: {text_result[:500]}")
            st.error("⚠️ Meal Plan Error: Could not find expected JSON data in AI response.")
            st.info("Try generating again - sometimes the AI needs retry.")
            return None

        try:
            log.info(f"Meal Plan Found JSON block: {json_str[:300]}...")
            meal_data = json.loads(json_str)
            log.info("Meal plan JSON decoded successfully.")

            if "meal_plan" not in meal_data:
                log.error("Meal Plan Error: Decoded JSON missing 'meal_plan' key.")
                st.error("❌ Meal Plan Error: AI response missing 'meal_plan' data.")
                log.error("Structure of decoded JSON: %s", meal_data)
                return None

            final_plan_data = meal_data.get("meal_plan")

            if final_plan_data and (isinstance(final_plan_data, dict) or isinstance(final_plan_data, list)):
                data_type = "dictionary" if isinstance(final_plan_data, dict) else "list"
                log.info(f"Successfully extracted meal plan {data_type} with {len(final_plan_data)} entries.")
                return final_plan_data
            else:
                log.error("Meal Plan Error: Value under 'meal_plan' is not a non-empty list or dictionary.")
                st.error(f"❌ Meal Plan Error: AI returned unexpected data format (expected List or Dict, got {type(final_plan_data)}).")
                log.error("Full Decoded JSON: %s", meal_data)
                return None

        except json.JSONDecodeError as e:
            log.error(f"Failed to decode meal plan JSON block: {e}")
            log.error(f"Problematic JSON string: {json_str[:500]}...")
            st.error(f"⚠️ Meal Plan Error: Failed to decode AI response data: {e}")
            return None

    except requests.exceptions.HTTPError as e:
        log.error(f"API HTTP Error (Meal Plan): {e}")
        _handle_groq_http_error(e, "Meal plan generation")
        return None
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


def generate_grocery_list_with_rest(api_key: str, meal_plan_dict: dict, language: str = "English"):
    """
    Generates a grocery list string using Groq API based on dish names.
    Returns a Markdown string or None on failure.
    """
    log.info("Entering generate_grocery_list_with_rest")
    if not api_key:
        log.error("API key is missing for generate_grocery_list_with_rest.")
        st.error("Configuration error: API Key not provided.")
        return None
    if not meal_plan_dict or not isinstance(meal_plan_dict, dict):
        log.warning("Invalid or empty meal_plan_dict provided for grocery list.")
        return None

    all_dishes = []
    try:
        for day_key, day_content in meal_plan_dict.items():
            if not isinstance(day_content, dict):
                continue
            for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
                info = day_content.get(meal_type)
                if isinstance(info, dict):
                    suffix = ""
                    i = 1
                    while True:
                        dish_key = f"dish_name{suffix}"
                        if dish_key in info:
                            dish_name = info.get(dish_key)
                            if dish_name and isinstance(dish_name, str) and dish_name.strip():
                                all_dishes.append(dish_name.strip())
                            i += 1
                            suffix = str(i)
                        elif suffix == "" and "dish_name" in info:
                            break
                        elif suffix != "":
                            break
                        else:
                            break
                elif isinstance(info, list):
                    for item in info:
                        if isinstance(item, dict) and "dish_name" in item:
                            dish_name = item.get("dish_name")
                            if dish_name and isinstance(dish_name, str) and dish_name.strip():
                                all_dishes.append(dish_name.strip())

        if not all_dishes:
            log.warning("No dish names extracted from meal plan for grocery list.")
            st.warning("No dish names found in the plan to create a grocery list.")
            return None

        unique_dishes = sorted(list(set(filter(None, all_dishes))))
        if not unique_dishes:
            log.warning("Filtered dish list for grocery list is empty.")
            st.warning("No valid dish names found to generate grocery list.")
            return None

        dishes_text = ", ".join(unique_dishes)
        log.info(f"Generating grocery list for {len(unique_dishes)} unique dishes: {dishes_text[:200]}...")

        prompt = f"""Act as a helpful shopping assistant. Based *only* on the following list of meal dishes planned for a week, generate a likely grocery list of ingredients needed.

Dishes Planned:
{dishes_text}

Instructions for Grocery List:
- List necessary ingredients to make these dishes in {language}.
- Combine similar items. Estimate reasonable weekly quantities for one person (e.g., "Onions: 2-3", "Chicken Breast: 1.5 lbs / 700g").
- Group ingredients into logical categories using Markdown H3 headings (### Category Name).
- Exclude: salt, black pepper, water, basic vegetable/canola oil.
- Format the output *only* as a Markdown list with bullet points (*) under category headings.
- Do NOT include introductory or concluding sentences. Just the list."""

        messages = [{"role": "user", "content": prompt}]
        
        log.info("Making API call for grocery list with model fallback...")
        response, used_model = _call_groq_with_fallback(
            api_key=api_key,
            messages=messages,
            temperature=0.3,
            max_tokens=1500,
            feature_name="grocery list generation"
        )
        log.info(f"Grocery List API Status Code: {response.status_code}")
        log.info(f"Used model: {used_model}")
        log.info(f"Grocery List Raw Response Text (first 500): {response.text[:500]}")

        response.raise_for_status()

        result_json = response.json()
        if not result_json.get("choices"):
            log.error("Grocery List Error: No 'choices' in response.")
            st.error("❌ Grocery List Error: AI service did not provide a valid response.")
            return None

        try:
            grocery_list_text = result_json["choices"][0]["message"]["content"]
            log.info("Successfully extracted grocery list text.")

            if grocery_list_text:
                log_entry = {
                    "timestamp": pd.Timestamp.now(tz='UTC').isoformat(),
                    "function_called": "generate_grocery_list",
                    "input_context": {
                        "language": language,
                        "meal_plan_keys": list(meal_plan_dict.keys()),
                        "api_provider": "groq"
                    },
                    "raw_response_text": grocery_list_text
                }
                try:
                    with open("api_log.jsonl", "a", encoding="utf-8") as f:
                        json.dump(log_entry, f)
                        f.write("\n")
                    log.info("Logged grocery list request/response")
                except Exception as log_e:
                    log.error(f"Failed to log grocery list: {log_e}")

            grocery_list_text = re.sub(r"^```markdown\s*\n?", "", grocery_list_text, flags=re.IGNORECASE | re.MULTILINE)
            grocery_list_text = re.sub(r"\n?```\s*$", "", grocery_list_text, flags=re.IGNORECASE | re.MULTILINE)
            return grocery_list_text.strip()

        except (KeyError, IndexError, TypeError) as e:
            log.error(f"Grocery List Error: Could not extract text part: {e}")
            st.error("❌ Grocery List Error: Could not process response from AI.")
            log.error("Full API Response: %s", result_json)
            return None

    except requests.exceptions.HTTPError as e:
        log.error(f"API HTTP Error (Grocery List): {e}")
        _handle_groq_http_error(e, "Grocery list generation")
        return None
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
