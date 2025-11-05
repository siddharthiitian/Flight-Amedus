# Deploying to Streamlit Cloud

This guide will help you deploy your AI Travel Planner app to Streamlit Cloud for free.

## Prerequisites

1. **GitHub Account**: You need a GitHub account to deploy on Streamlit Cloud
2. **GitHub Repository**: Your code should be pushed to a GitHub repository

## Step 1: Push Your Code to GitHub

1. Initialize git (if not already done):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. Create a new repository on GitHub (https://github.com/new)

3. Push your code:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git branch -M main
   git push -u origin main
   ```

## Step 2: Deploy to Streamlit Cloud

1. Go to [Streamlit Cloud](https://share.streamlit.io/)
2. Sign in with your GitHub account
3. Click **"New app"**
4. Select your repository and branch
5. Set the **Main file path** to: `streamlit_app.py`
6. Click **"Deploy!"**

## Step 3: Configure Secrets

After deployment, you need to add your API keys as secrets:

1. In your Streamlit Cloud dashboard, click on your app
2. Click **"Settings"** (⚙️ icon)
3. Click **"Secrets"** tab
4. Add your secrets in this format:

```toml
GROK_API_KEY = "your_grok_api_key_here"
GROK_BASE_URL = "https://api.x.ai/v1"
GROK_MODEL = "grok-2-latest"

GEMINI_API_KEY = "your_gemini_api_key_here"
GEMINI_MODEL = "gemini-2.5-flash"

AMADEUS_API_KEY = "your_amadeus_key_here"
AMADEUS_API_SECRET = "your_amadeus_secret_here"
AMADEUS_ENV = "test"

DEFAULT_CURRENCY = "USD"
```

5. Click **"Save"** - your app will automatically redeploy with the new secrets

## Step 4: Access Your Live App

Once deployed, you'll get a live URL like:
```
https://your-app-name.streamlit.app
```

You can share this link with anyone!

## Important Notes

- **Never commit your `keys.env` file** - Make sure it's in `.gitignore`
- **Use Streamlit Secrets** for API keys in production (not keys.env)
- **Free tier limits**: Streamlit Cloud free tier has usage limits
- **Auto-deploy**: Your app automatically redeploys when you push changes to GitHub

## Troubleshooting

### App won't start
- Check that `streamlit_app.py` is in the root directory
- Verify all dependencies are in `requirements.txt`
- Check the logs in Streamlit Cloud dashboard

### API keys not working
- Verify secrets are set correctly in Streamlit Cloud Settings → Secrets
- Check for typos in secret names (they're case-sensitive)
- Make sure you're not using quotes around the values in secrets

### Dependencies issues
- Ensure all packages are in `requirements.txt`
- Check that version numbers are compatible
- Review deployment logs for specific errors

## Updating Your App

1. Make changes to your code locally
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Update description"
   git push
   ```
3. Streamlit Cloud will automatically redeploy your app

## Security Best Practices

- ✅ Use Streamlit Secrets for sensitive data
- ✅ Never commit API keys to GitHub
- ✅ Use environment-specific secrets (test vs production)
- ✅ Regularly rotate your API keys
- ✅ Monitor your API usage

