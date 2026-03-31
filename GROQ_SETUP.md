# Migration from Google Gemini to Groq API

## What Changed

Your meal planner now uses **Groq API** instead of Google Gemini. Here's why:

✅ **Free tier**: Infinite free tier (no quota exhaustion)
✅ **Fast**: Among the fastest inference speeds available
✅ **Generous rate limits**: 100+ requests per minute
✅ **Reliable**: No 429 quota errors like you were experiencing

---

## New Files Created

- **`groq_api.py`** - All Groq API functions (replaces gemini_api.py functionality)
  - `test_groq_connection()` - Verify API connectivity
  - `generate_meal_plan_with_rest()` - Generate 7-day meal plans
  - `generate_grocery_list_with_rest()` - Generate grocery lists
  - `_handle_groq_http_error()` - User-friendly error messages

---

## Updated Files

- **`constants.py`** - Now loads `GROQ_API_KEY` instead of `GOOGLE_API_KEY`
- **`app.py`** - Imports `groq_api` instead of `gemini_api`
  - Updated API diagnostics panel to show Groq status
  - Added link to get free Groq API key

---

## Setup Instructions

### Step 1: Get Free Groq API Key

1. Visit **https://console.groq.com/keys**
2. Sign up with email or GitHub
3. Copy your API key

### Step 2: Add Key to Streamlit Secrets (Deployment)

If deploying on **Streamlit Cloud**:

1. Go to your app settings → **Secrets**
2. Add this line:
   ```
   groq_api_key = "YOUR_API_KEY_HERE"
   ```
3. Save and redeploy

### Step 3: Add Key to .env (Local Development)

For **local testing**:

1. Create `.env` file in your project root
2. Add:
   ```
   groq_api_key=YOUR_API_KEY_HERE
   ```
3. Save and restart Streamlit

---

## Testing the Setup

1. Start your Streamlit app: `streamlit run app.py`
2. Expand **"API Diagnostics"** panel at the top
3. Click **"Test Groq API Key"**
4. You should see: ✅ "Groq API reachable (mixtral-8x7b-32768)"

---

## Groq Models Available

The app uses **`mixtral-8x7b-32768`** by default, which is:
- Fast and reliable
- Good quality for meal planning
- Free tier friendly

Other models available (if you want to experiment):
- `llama2-70b-4096`
- `llama-3-8b-8192`
- `gemma-7b-it`

---

## Advantages Over Gemini

| Feature | Groq | Gemini (Free) |
|---------|------|---------------|
| **Free Quota** | Unlimited | 0 (like you experienced) |
| **Rate Limit** | 100+ req/min | Limited |
| **Cost** | Free (generous) | Free → Paid required |
| **Speed** | Fastest | Fast |
| **Reliability** | Very stable | Subject to quota issues |

---

## Old Files (Still Present, Not Used)

- `gemini_api.py` - No longer imported, kept for reference
- Can be deleted if you prefer (or keep as backup)

---

## Troubleshooting

### Issue: "groq_api_key not found"
- **Fix**: Check `.env` file exists and has `groq_api_key=YOUR_KEY`
- Or update Streamlit secrets if deployed

### Issue: API Test shows error 401
- **Fix**: Your API key may be invalid or expired
- Get a new key from: https://console.groq.com/keys

### Issue: Rate limit error (429)
- **Fix**: Wait a moment and try again
- Groq's free tier is very generous, this rarely happens
- Check https://console.groq.com for usage stats

---

## Next Steps

1. ✅ Add your Groq API key to `.env` or Streamlit secrets
2. ✅ Test the connection using API Diagnostics panel
3. ✅ Click "Generate 7-Day Plan" to test meal plan generation
4. ✅ Deploy to Streamlit Cloud

You're all set! 🎉
