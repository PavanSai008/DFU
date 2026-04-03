# Deployment Guide — Free Hosting Options

Your DFU Analyzer is now ready to deploy! Flask serves both the backend API and frontend from a single server. This guide covers 3 **free** options.

---

## Option 1: Railway (Recommended — Most Generous Free Tier)

Railway gives you **$5/month** free credits (enough for continuous hosting).

### Step 1: Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub/email
3. Create a new project

### Step 2: Connect GitHub Repository
1. In Railway, click "New Project" → "Deploy from GitHub repo"
2. Authorize Railway to access your GitHub account
3. Select your `dfu_final` repository
4. Railway will auto-detect `Dockerfile` and start building

### Step 3: Configure Environment
1. Go to **Variables** tab
2. Add if needed (optional):
   ```
   PORT=5000
   ```
3. Railway auto-detects Dockerfile, no other config needed

### Step 4: View Deployed App
✅ Your app will be live at: `https://dfu-final-production.railway.app` (auto-generated URL)

**Cost**: FREE ($5/month credits) | **Uptime**: 24/7

---

## Option 2: Render (Free but sleepy)

Render has a true free tier, but spins down inactive apps (takes 30sec to wake up).

### Step 1-2: Sign up & Connect GitHub
1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Click "New +" → "Web Service"
4. Connect your GitHub repo

### Step 3: Configure
- **Name**: `dfu-analyzer`
- **Environment**: `Docker`
- **Region**: Choose closest to you
- **Plan**: Free

### Step 4: Deploy
Click "Create Web Service" → wait ~3min for build

✅ Live at: `https://dfu-analyzer.onrender.com`

**Cost**: FREE | **Uptime**: 24/7 (spins down after 15min inactivity)

---

## Option 3: Replit (Good for testing)

Replit is instant and great for quick testing.

### Step 1: Import from GitHub
1. Go to [replit.com](https://replit.com)
2. Click "Create" → "Import from GitHub"
3. Paste your repo URL
4. Wait for import (2-5 min)

### Step 2: Run
1. Replit auto-detects `requirements.txt`
2. Click the "Run" button
3. Choose "bash" terminal, run:
   ```bash
   cd backend
   python app.py
   ```

✅ Your app is live on the Replit URL (shown in IDE)

**Cost**: FREE | **Limitations**: Sleeps when inactive, slower than Railway/Render

---

## Before Deploying — Model Files

⚠️ Your model weights file (`model_weights.weights.h5`) is **too large** (~300MB) to commit to Git.

### Solution: GitHub Releases (Free)

1. **Compress locally**:
   ```bash
   cd backend/models
   tar.gz model_weights.weights.h5  # or zip on Windows
   ```

2. **Create GitHub Release**:
   - Go to your repo → "Releases" → "Create new release"
   - Tag: `v1.0.0-model`
   - Upload compressed file
   - Publish

3. **Update Dockerfile** to download on startup:
   ```dockerfile
   RUN wget https://github.com/YOUR_USERNAME/dfu_final/releases/download/v1.0.0-model/model_weights.weights.h5 -O backend/models/model_weights.weights.h5
   ```

OR skip this and:
- Push to your GitHub PRIVATE repo (if using Railway/Render)
- They'll clone it fully, including .gitignore'd files... actually NO, .gitignore still applies.

**Better approach**: Use GitHub Releases as above.

---

## Testing Locally Before Deploy

```bash
# Test locally first
cd backend
python app.py

# Visit: http://localhost:5000
# Upload a test image → verify it works
```

---

## Post-Deployment

### Check Status
Visit your deployed URL in browser. You should see:
- ✅ DFU Analyzer interface loads
- ✅ "Model ready: ✓" badge in header
- ✅ File upload works

### View Logs
**Railway**: Click app → "Logs" tab
**Render**: App dashboard → "Logs"
**Replit**: Shows in terminal

### If Model Fails to Load
- Check logs for "Model not loaded" error
- Verify `model_weights.weights.h5` exists in `backend/models/`
- Re-download from GitHub Releases if needed

---

## Updating Code After Deployment

### For Railway/Render:
1. Commit changes to GitHub
2. Push to repo
3. They auto-redeploy on push (can disable in settings)

### For Replit:
1. Edit code in Replit IDE
2. Or push to GitHub and re-import

---

## What If I Want My Own Domain?

### Railway / Render
Both support custom domains:
- Buy domain (GoDaddy, Namecheap, etc.) — ~$10/year
- Connect to Railway/Render in settings
- Add CNAME record in domain registrar

### Example
- Railway App: `dfu-final-production.railway.app`
- Domain: `dfu.mysite.com`
- Point `mydomain.com` → Railway's IP/CNAME

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Model not loading | Check model_weights.weights.h5 exists + correct path |
| "Cannot find module X" | requirements.txt missing dependency |
| Frontend says "API Error" | Backend not running or CORS issue |
| Takes 30sec to load | Render free tier — spins down after inactivity |

---

## Summary

| Service | Cost | Uptime | Ease |
|---------|------|--------|------|
| **Railway** ⭐ | $5/mo free | 24/7 | Very easy |
| Render | Free | 24/7 (sleepy) | Easy |
| Replit | Free | Sleepy | Instant |

**Recommendation**: Railway (generous free tier, always-on, auto-deploys from Git)

---

**Done!** Your DFU Analyzer is deployment-ready. Pick a platform above and you'll be live in minutes! 🚀
