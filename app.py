# app.py - Modern Meal Planner with Day Tabs

import os
import re
import logging
import pandas as pd
import streamlit as st

# Custom modules
import meal_utils as utils
import gemini_api

import plotly.graph_objects as go

# --- Page Config ---
st.set_page_config(
    page_title="Meal Planner", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Logging & Env Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Import API key from constants (handles both local and deployment scenarios)
from constants import GOOGLE_API_KEY

if not GOOGLE_API_KEY:
    st.error("⚠️ `google_api_key` not found. Please configure it in Streamlit secrets or .env file.")
    st.info("For Streamlit Cloud: Add your API key in the secrets management section.")
    st.info("For local development: Add GOOGLE_API_KEY to your .env file.")
    st.stop()

# --- Clean UI Styling ---
st.markdown("""
<style>
    /* Hide dark header */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* Force white background and dark text everywhere */
    .stApp, .main, .block-container, div[data-testid="stAppViewContainer"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        padding-top: 1rem !important;
    }
    
    /* Force all headers to be dark */
    h1, h2, h3, h4, h5, h6 {
        color: #000000 !important;
        font-weight: bold !important;
    }
    
    /* Force all labels and text to be dark */
    label, p, span, div, .stMarkdown, .stText {
        color: #000000 !important;
    }
    
    /* Force form elements to be dark */
    .stTextInput label, .stNumberInput label, .stSelectbox label, 
    .stRadio label, .stForm label {
        color: #000000 !important;
        font-weight: 500 !important;
    }
    
    /* Force input text to be dark with white background */
    input, select, textarea {
        color: #000000 !important;
        background-color: #ffffff !important;
    }
    
    /* Style dropdowns - comprehensive fix */
    .stSelectbox > div > div, .stSelectbox div[data-baseweb="select"], 
    .stMultiSelect > div > div, .stMultiSelect div[data-baseweb="select"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #ccc !important;
    }
    
    /* Style dropdown options */
    .stSelectbox div[data-baseweb="popover"] div, 
    .stMultiSelect div[data-baseweb="popover"] div {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    /* Style dropdown text */
    .stSelectbox div[data-testid="stSelectbox"] div,
    .stMultiSelect div[data-testid="stMultiSelect"] div {
        color: #000000 !important;
        background-color: #ffffff !important;
    }
    
    /* Force multiselect styling */
    div[data-baseweb="select"] {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    /* Aggressive fix for the specific dark dropdown */
    .stMultiSelect div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    /* Target the inner select element directly */
    div[data-baseweb="select"] span, div[data-baseweb="select"] > div > div {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    /* Fix dataframe tables - force white background and dark text */
    .stDataFrame, .stDataFrame > div, .stDataFrame table {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    /* Fix dataframe headers and cells */
    .stDataFrame th, .stDataFrame td {
        background-color: #ffffff !important;
        color: #000000 !important;
        border-color: #ddd !important;
    }
    
    /* Fix dataframe header row */
    .stDataFrame thead tr {
        background-color: #f8f9fa !important;
    }
    
    /* Fix dataframe body rows */
    .stDataFrame tbody tr {
        background-color: #ffffff !important;
    }
    
    /* More aggressive table fixes */
    div[data-testid="stDataFrame"], div[data-testid="stDataFrame"] > div,
    div[data-testid="stDataFrame"] table, div[data-testid="stDataFrame"] tbody,
    div[data-testid="stDataFrame"] thead {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    /* Force all table cells */
    div[data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] th {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #ddd !important;
    }
    
    /* Ultra aggressive table fixes - try everything */
    [data-testid="stDataFrame"] * {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    /* Target specific table classes */
    .dataframe, .dataframe td, .dataframe th {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    /* Style ALL buttons including form submit buttons */
    .stButton > button, .stFormSubmitButton > button, button[kind="primary"], button[type="submit"] {
        background-color: #4CAF50 !important; 
        color: #ffffff !important; 
        border-radius: 8px !important;
        border: none !important;
        padding: 0.5rem 1rem !important;
        font-weight: 600 !important;
        font-size: 16px !important;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover, button[kind="primary"]:hover, button[type="submit"]:hover {
        background-color: #45a049 !important;
    }
    
    /* Target form submit button specifically */
    .stForm button {
        background-color: #4CAF50 !important; 
        color: #ffffff !important; 
        border-radius: 8px !important;
        border: none !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 16px !important;
    }
    .stForm button:hover {
        background-color: #45a049 !important;
    }
    
    /* Fix radio buttons */
    .stRadio > div {
        color: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- App Title ---
st.title("🍴 Modern Meal Planner")  # Force deployment refresh

# --- User Form ---
st.header("Generate Personalized Meal Plan")
with st.form("user_profile_form"):
    st.write("Fill in your details to generate a 7-day plan:")

    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age", min_value=10, max_value=100, value=30, step=1)
        weight = st.number_input("Weight (kg)", min_value=30.0, value=70.0, step=0.5)
        height = st.number_input("Height (cm)", min_value=100.0, value=170.0, step=0.5)
    with col2:
        gender = st.radio("Biological Sex:", ["Male", "Female"], index=0, horizontal=True)
        activity = st.selectbox("Activity Level:", ["Sedentary", "Light", "Moderate", "Active", "Very Active"], index=2)
        goal = st.selectbox("Primary Goal:", ["Lose Weight", "Maintain Weight", "Gain Muscle"], index=1)

    st.markdown("---")
    restrictions = st.multiselect("Dietary Restrictions / Preferences:", ["Vegetarian", "Vegan", "Gluten-Free", "Dairy-Free", "Nut-Free","Low Carb"])
    favorites = st.text_input("Favorite Foods (comma-separated, optional):", placeholder="e.g., Salmon, Avocado, Berries")
    dislikes = st.text_input("Disliked Foods (comma-separated, optional):", placeholder="e.g., Mushrooms, Olives")

    submitted = st.form_submit_button("Generate 7-Day Plan")

# --- Generate Meal Plan ---
if submitted:
    calculated_calories = utils.calculate_calories(age, weight, height, gender, activity, goal)
    if calculated_calories:
        st.info(f"Targeting approximately **{calculated_calories} kcal/day**. Generating plan...")
        user_prefs = {"goal": goal, "restrictions": restrictions, "favorites": favorites, "dislikes": dislikes}

        with st.spinner("Creating your meal plan..."):
            meal_plan_dict_result = gemini_api.generate_meal_plan_with_rest(GOOGLE_API_KEY, calculated_calories, user_prefs)

        if meal_plan_dict_result and isinstance(meal_plan_dict_result, dict):
            st.session_state['meal_plan_data'] = meal_plan_dict_result
            st.success("✅ Meal plan generated successfully!")
        else:
            st.error("Could not generate meal plan. Please try again.")

# --- Display Meal Plan with Tabs ---
if 'meal_plan_data' in st.session_state and st.session_state['meal_plan_data']:
    meal_plan_data = st.session_state['meal_plan_data']
    st.header("📅 7-Day Meal Plan")

    weekly_summary = {"Day": [], "Calories": [], "Protein": [], "Carbs": [], "Fat": []}

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    sorted_items = sorted(
        meal_plan_data.items(),
        key=lambda item: int(re.search(r'\d+', item[0]).group()) if re.search(r'\d+', item[0]) else 0
    )

    tabs = st.tabs(day_names)

    for tab, (day_key, day_content) in zip(tabs, sorted_items):
        with tab:
            st.subheader(day_key)
            meal_rows, daily_calories, daily_protein, daily_carbs, daily_fat = utils.process_day_content(day_content)
            
            if meal_rows:
                df = pd.DataFrame(meal_rows)
                st.dataframe(df, hide_index=True, width="stretch")

            # Macro pie chart
            fig_macros = go.Figure(
                data=[go.Pie(
                    labels=["Protein", "Carbs", "Fat"],
                    values=[daily_protein*4, daily_carbs*4, daily_fat*9],
                    hole=0.4,
                    marker=dict(colors=['#FF6361', '#58508D', '#FFA600'])
                )]
            )
            fig_macros.update_layout(
                title_text="Macros Breakdown", 
                title_x=0.5,
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color='black')
            )
            st.plotly_chart(fig_macros, use_container_width=True, config={"displayModeBar": False})

            # Daily totals
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Calories", f"{utils.format_number(daily_calories)} kcal")
            c2.metric("Protein", f"{utils.format_number(daily_protein)} g")
            c3.metric("Carbs", f"{utils.format_number(daily_carbs)} g")
            c4.metric("Fat", f"{utils.format_number(daily_fat)} g")

            # Add to weekly summary
            weekly_summary["Day"].append(day_key)
            weekly_summary["Calories"].append(daily_calories)
            weekly_summary["Protein"].append(daily_protein)
            weekly_summary["Carbs"].append(daily_carbs)
            weekly_summary["Fat"].append(daily_fat)

    # Weekly trends chart
    st.markdown("---")
    st.subheader("📈 Weekly Nutrient Trends")
    weekly_df = pd.DataFrame(weekly_summary)
    fig_weekly = go.Figure()
    fig_weekly.add_trace(go.Bar(name="Calories", x=weekly_df["Day"], y=weekly_df["Calories"], marker_color="#4CAF50"))
    fig_weekly.add_trace(go.Bar(name="Protein", x=weekly_df["Day"], y=weekly_df["Protein"], marker_color="#FF6361"))
    fig_weekly.add_trace(go.Bar(name="Carbs", x=weekly_df["Day"], y=weekly_df["Carbs"], marker_color="#58508D"))
    fig_weekly.add_trace(go.Bar(name="Fat", x=weekly_df["Day"], y=weekly_df["Fat"], marker_color="#FFA600"))
    fig_weekly.update_layout(
        barmode='group', 
        xaxis_title="Day", 
        yaxis_title="Amount", 
        title="Weekly Nutrition Overview",
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color='black')
    )
    st.plotly_chart(fig_weekly, use_container_width=True, config={"displayModeBar": False})

# --- Grocery List ---
st.markdown("---")
if st.button("Generate Weekly Grocery List"):
    current_meal_plan_data = st.session_state.get('meal_plan_data')
    if current_meal_plan_data:
        with st.spinner("Creating grocery list..."):
            grocery_list_md = gemini_api.generate_grocery_list_with_rest(GOOGLE_API_KEY, current_meal_plan_data)

        if grocery_list_md:
            st.subheader("🛒 Weekly Grocery List")
            st.markdown(grocery_list_md)
            st.caption("Note: This is an automatically generated estimate.")
