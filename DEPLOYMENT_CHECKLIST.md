# Before You Deploy — Checklist ✓

Follow these steps to prepare for deployment:

## 1. Test Locally First
```bash
cd backend
python app.py
```
Visit `http://localhost:5000` and upload a test image.

✅ Expected: Model loads, predictions work, frontend displays results

---

## 2. Prepare Model Files for Deployment

Your `model_weights.weights.h5` is too large (~300MB) to push to Git. Use GitHub Releases:

### macOS/Linux:
```bash
cd backend/models
zip model_weights.zip model_weights.weights.h5
cd ../..
```

### Windows (PowerShell):
```powershell
cd backend\models
Compress-Archive -Path model_weights.weights.h5 -DestinationPath model_weights.zip
cd ..\..
```

---

## 3. Push Code to GitHub

```bash
# Initialize git (if not done)
git init
git add .
git commit -m "Initial DFU Analyzer commit"

# Add your GitHub repo URL (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/dfu_final.git
git branch -M main
git push -u origin main
```

---

## 4. Create GitHub Release with Model

1. Go to **GitHub repo** → **Releases** → **Create a new release**
2. Set tag to: `v1.0.0-model`
3. Title: `Model Weights`
4. Upload: `backend/models/model_weights.zip`
5. Click **Publish release**

Get the download URL (you'll need this for Dockerfile update if deploying to Railway/Render)

---

## 5. Deploy

Pick ONE:

### Railway (Recommended)
```
1. Go to railway.app
2. New project → Deploy from GitHub
3. Select your dfu_final repo
4. Railway auto-builds from Dockerfile (no config needed)
5. Live in ~3-5 minutes
```

### Render
```
1. Go to render.com
2. New Web Service → Connect GitHub
3. Select dfu_final repo, choose "Docker"
4. Click Deploy
5. Live in ~5-10 minutes
```

### Replit (Quick Test)
```
1. Go to replit.com
2. Create → Import from GitHub
3. Paste repo URL
4. Click "Run" when ready
5. Live instantly
```

---

## 6. Handle Missing Model File

When deployed, carriers may need to download the model separately OR you can auto-download in Dockerfile.

### Option A: Manual Download (User responsibility)
Users download `model_weights.zip` from GitHub Releases, extract to `backend/models/`, restart.

### Option B: Auto-Download in Dockerfile (Better UX)
Before deploying to Railway/Render, update `Dockerfile`:

Replace:
```dockerfile
COPY backend/ ./backend/
COPY frontend/ ./frontend/
```

With:
```dockerfile
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Download model weights from GitHub Releases
RUN mkdir -p backend/models && \
    cd backend/models && \
    wget https://github.com/YOUR_USERNAME/dfu_final/releases/download/v1.0.0-model/model_weights.zip && \
    unzip -q model_weights.zip && \
    rm model_weights.zip && \
    cd /app
```

(Replace `YOUR_USERNAME` with your actual GitHub username)

Then push to GitHub and deploy.

---

## 7. Verify Deployment

Once live, visit your deployment URL:
- ✅ Page loads with dark theme
- ✅ Header shows "Model ready: ✓" 
- ✅ File upload works
- ✅ Test with a sample wound image

---

## 8. (Optional) Add Custom Domain

If you want `mydfu.health` instead of `dfu-final-production.railway.app`:

1. Buy domain (~$10/year from GoDaddy, Namecheap, etc.)
2. In Railway/Render settings, add "Custom Domain"
3. Update your domain registrar's CNAME record
4. Wait ~15 min for DNS propagation

---

## Quick Reference

| Step | Command | Time |
|------|---------|------|
| Test locally | `cd backend && python app.py` | 2 min |
| Push to GitHub | See step 3 | 2 min |
| Create Release | GitHub web UI | 3 min |
| Deploy (Railway) | Click "Deploy from GitHub" | 3-5 min |
| | **Total** | **~15 min** |

---

**Your app is ready to be world-accessible!** 🌍
