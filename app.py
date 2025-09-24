# app.py - Modern Meal Planner with Day Tabs

import os
import re
import logging
import pandas as pd
import streamlit as st

# Custom modules
import utils
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

# --- Custom CSS ---
st.markdown("""
<style>
    /* Force light mode */
    .stApp {
        background-color: #ffffff !important;
    }
    
    /* Hide Streamlit header, menu, and footer */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* Hide main menu */
    .css-1rs6os, .css-17ziqus {
        display: none !important;
    }
    
    /* Hide hamburger menu */
    button[kind="header"] {
        display: none !important;
    }
    
    /* Hide deploy button */
    .css-1x8cf1d, .css-uf99v8 {
        display: none !important;
    }
    
    /* Hide fork button and toolbar */
    .css-14xtw13, .css-k0sv6k {
        display: none !important;
    }
    
    /* Hide GitHub corner banner */
    .github-corner {
        display: none !important;
    }
    
    /* Hide footer */
    footer {
        display: none !important;
    }
    
    /* Hide "Made with Streamlit" */
    .css-1v0mbdj, .css-1wrcr25 {
        display: none !important;
    }
    
    /* Hide red crown and profile elements - COMPREHENSIVE */
    .css-1kyxreq, .css-2trqyj, .css-1v3fvcr {
        display: none !important;
    }
    
    /* Hide ViewerBadge (red crown) - ALL VARIANTS */
    .viewerBadge_container__1QSob,
    .viewerBadge_link__1S137,
    [data-testid="stToolbar"],
    [data-testid="manage-app-button"],
    .stToolbar,
    .stDeployButton,
    .css-vk3wp9,
    .css-12oz5g7,
    .css-1n76uvr,
    .css-1wbqy5l {
        display: none !important;
    }
    
    /* STREAMLIT CLOUD SPECIFIC - Hide deployment elements */
    .stAppViewContainer > div:last-child,
    .stApp > div:last-child,
    div[data-testid="stSidebar"] + div + div,
    .main > div:last-child,
    .stAppEmbeddingId-root div:last-child {
        display: none !important;
    }
    
    /* Hide Streamlit Cloud footer and profile */
    .css-1rs6os.e1fqkh3o3,
    .css-1d391kg,
    .css-18ni7ap.e1fqkh3o1,
    .css-qrbaxs,
    .css-1inwz65.e1fqkh3o4,
    .css-1lcbmhc.e1fqkh3o10,
    .css-1outpf7.e1fqkh3o11 {
        display: none !important;
    }
    
    /* Hide "Made with Streamlit" cloud version */
    a[href*="streamlit.io"],
    a[target="_blank"][href*="streamlit"],
    .css-cio0fg,
    .css-1fb8w7d {
        display: none !important;
    }
    
    /* Hide cloud-specific toolbar */
    .toolbar,
    .stAppToolbar,
    [class*="toolbar"],
    [class*="Toolbar"] {
        display: none !important;
    }
    
    /* Hide bottom status bar and profile */
    .stStatusWidget,
    .css-1dp5vir,
    .css-17ziqus,
    .css-1544g2n,
    .css-1d391kg,
    .css-18ni7ap,
    .css-qrbaxs,
    div[data-stale="false"] {
        display: none !important;
    }
    
    /* Hide any bottom floating elements */
    .css-1outpf7,
    .css-1lcbmhc,
    .css-1y4p8pa,
    .css-12ttj6m,
    .css-1inwz65 {
        display: none !important;
    }
    
    /* Target specific bottom-right elements */
    .css-1y4p8pa > div,
    .css-12ttj6m > div,
    div[style*="position: fixed"][style*="bottom"],
    div[style*="position: absolute"][style*="bottom"] {
        display: none !important;
    }
    
    /* Specific bottom elements only */
    div[style*="position: fixed"][style*="bottom: 16px"][style*="right"],
    div[style*="position: fixed"][style*="bottom: 0px"][style*="right"],
    div[class*="viewerBadge"],
    div[class*="toolbar"] {
        display: none !important;
    }
    
    /* Hide by content - target links with streamlit */
    a[href*="streamlit.io"],
    img[alt*="Streamlit"] {
        display: none !important;
    }
    
    /* Main content styling */
    body {background-color: #ffffff !important;}
    .block-container {padding: 2rem;}
    h1, h2, h3, h4 {color: #2c3e50; font-family: 'Helvetica Neue', sans-serif;}
    .stButton > button {
        background-color: #4CAF50; color: white; border: none; border-radius: 12px;
        padding: 0.6rem 1.2rem; font-size: 16px; font-weight: 600; transition: 0.3s;
    }
    .stButton > button:hover {background-color: #45a049; transform: scale(1.02);}
    .stDataFrame {border-radius: 12px; border: 1px solid #ddd; box-shadow: 0px 2px 6px rgba(0,0,0,0.05);}
    [data-testid="stMetricValue"] {font-size: 22px; font-weight: 700; color: #2c3e50;}
    [data-testid="stMetricLabel"] {font-size: 14px; font-weight: 500; color: #555;}
    .streamlit-expanderHeader {font-weight: bold; color: #2c3e50;}
    hr {border: none; height: 1px; background-color: #e0e0e0;}
    
    /* Additional cleanup for deployment elements */
    .stAlert, .stException {
        margin-top: 0 !important;
    }
</style>

<script>
// Aggressive removal of all bottom elements and toolbars (CLOUD + LOCAL)
function removeStreamlitElements() {
    const elementsToRemove = [
        // Toolbar and deploy elements
        '.viewerBadge_container__1QSob',
        '.viewerBadge_link__1S137',
        '[data-testid="stToolbar"]',
        '[data-testid="manage-app-button"]',
        '.stToolbar',
        '.stDeployButton',
        'header[data-testid="stHeader"]',
        
        // Profile and status elements
        '.css-1kyxreq',
        '.css-2trqyj', 
        '.css-1v3fvcr',
        '.css-vk3wp9',
        '.css-12oz5g7',
        '.css-1n76uvr',
        '.css-1wbqy5l',
        '.stStatusWidget',
        '.css-1dp5vir',
        '.css-1544g2n',
        '.css-1d391kg',
        '.css-18ni7ap',
        '.css-qrbaxs',
        
        // Bottom floating elements
        '.css-1outpf7',
        '.css-1lcbmhc',
        '.css-1y4p8pa',
        '.css-12ttj6m',
        '.css-1inwz65',
        
        // STREAMLIT CLOUD SPECIFIC
        '.css-1rs6os.e1fqkh3o3',
        '.css-18ni7ap.e1fqkh3o1',
        '.css-1inwz65.e1fqkh3o4',
        '.css-1lcbmhc.e1fqkh3o10',
        '.css-1outpf7.e1fqkh3o11',
        '.css-cio0fg',
        '.css-1fb8w7d',
        '.toolbar',
        '.stAppToolbar'
    ];
    
    elementsToRemove.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
            if (el) {
                el.style.display = 'none !important';
                el.remove();
            }
        });
    });
    
    // Remove specific bottom-right positioned elements only
    const bottomElements = document.querySelectorAll('div');
    bottomElements.forEach(el => {
        const style = window.getComputedStyle(el);
        
        // Only remove if it's bottom-right positioned AND small (likely a badge/toolbar)
        if (style.position === 'fixed' && 
            (style.bottom === '0px' || style.bottom === '16px') &&
            (style.right === '0px' || style.right === '16px') &&
            el.offsetWidth < 200 && el.offsetHeight < 100) {
            el.style.display = 'none';
        }
        
        // Remove by specific content only
        const text = el.textContent?.trim().toLowerCase();
        if (text && (
            text === 'made with streamlit' ||
            text.includes('deploy') && text.length < 20
        )) {
            el.style.display = 'none';
        }
    });
    
    // Remove Streamlit links specifically
    const streamlitLinks = document.querySelectorAll('a[href*="streamlit.io"]');
    streamlitLinks.forEach(el => el.style.display = 'none');
}

// Run immediately and then repeatedly
removeStreamlitElements();
setTimeout(removeStreamlitElements, 1000);
setTimeout(removeStreamlitElements, 3000);

// Also run when page changes
const observer = new MutationObserver(removeStreamlitElements);
observer.observe(document.body, { childList: true, subtree: true });
</script>
""", unsafe_allow_html=True)

# --- App Title ---
st.title("🍴 Modern Meal Planner")

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
                st.dataframe(df, hide_index=True, use_container_width=True)

            # Macro pie chart
            fig_macros = go.Figure(
                data=[go.Pie(
                    labels=["Protein", "Carbs", "Fat"],
                    values=[daily_protein*4, daily_carbs*4, daily_fat*9],
                    hole=0.4,
                    marker=dict(colors=['#FF6361', '#58508D', '#FFA600'])
                )]
            )
            fig_macros.update_layout(title_text="Macros Breakdown", title_x=0.5)
            st.plotly_chart(fig_macros, use_container_width=True)

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
    fig_weekly.update_layout(barmode='group', xaxis_title="Day", yaxis_title="Amount", title="Weekly Nutrition Overview")
    st.plotly_chart(fig_weekly, use_container_width=True)

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
