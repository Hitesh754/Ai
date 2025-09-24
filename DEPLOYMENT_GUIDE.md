# Streamlit Deployment Guide

## Issues Fixed

1. **API Key Configuration**: Updated `constants.py` to properly handle both local development (.env) and Streamlit Cloud (secrets) environments
2. **Dependency Issues**: Removed unused `dotenv` import from `app.py` and updated `requirements.txt` with correct package versions
3. **Error Handling**: Added better error messages that guide users on how to configure API keys for both local and cloud environments

## For Streamlit Cloud Deployment

### Step 1: Deploy to Streamlit Cloud
1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Select your repository and main branch
5. Set the main file path to `app.py`

### Step 2: Configure Secrets
1. In your Streamlit Cloud app dashboard, go to "Settings" → "Secrets"
2. Add your API keys in TOML format:
```toml
google_api_key = "your_actual_google_api_key_here"
usda_api_key = "your_actual_usda_api_key_here"
```

### Step 3: Deploy
Click "Deploy" and your app should work!

## For Local Development

Your app will continue to work locally using the `.env` file as before.

## Key Changes Made

- **constants.py**: Now properly handles both Streamlit secrets and local .env files
- **app.py**: Removed dotenv import and improved error handling
- **requirements.txt**: Updated with correct package names and versions
- **Added `.streamlit/secrets.toml`**: Template file showing the required structure

## Troubleshooting

If you still have issues:
1. Make sure your API keys are valid
2. Check that the secrets are properly configured in Streamlit Cloud
3. Verify all dependencies are in requirements.txt
4. Check the app logs in Streamlit Cloud for specific error messages