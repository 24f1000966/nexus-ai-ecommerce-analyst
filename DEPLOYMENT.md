# Deployment Guide — Nexus AI on Render + Neon

This guide deploys Nexus AI to **Render.com** (free tier) and **Neon** (free Postgres) for a fully live, shareable instance.

## Prerequisites

1. **GitHub Account** — Push your repo to GitHub (already done at `github.com/24f1000966/nexus-ai-ecommerce-analyst`)
2. **Render Account** — Sign up at https://render.com (free tier included)
3. **Neon Account** — Sign up at https://neon.tech (free tier: 10GB storage, 3 projects)

---

## Step 1: Create a Neon Postgres Database

1. Go to https://neon.tech and sign up
2. Create a new project: name it `nexus-ai`
3. Create a database: name it `platform`
4. Copy the connection string — it looks like:
   ```
   postgresql://neondb_owner:abcd1234@ep-cool-xyz.us-east-1.neon.tech/platform?sslmode=require
   ```
5. **Save this** — you'll need it in Step 3

---

## Step 2: Update Your GitHub Repo

Commit and push all changes:

```bash
git add .env.example DEPLOYMENT.md
git commit -m "Add deployment configuration for Render + Neon"
git push origin main
```

---

## Step 3: Deploy Backend on Render

1. Go to https://dashboard.render.com and sign in
2. Click **New +** → **Web Service**
3. **Connect Repository**: Select your GitHub repo (`nexus-ai-ecommerce-analyst`)
4. **Settings**:
   - Name: `nexus-ai-api`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn backend.main:api --host 0.0.0.0 --port 8000`
   - Plan: **Free** (auto-spins down after 15 min inactivity)
5. **Environment Variables** — add these:
   ```
   DATABASE_URL = [paste your Neon connection string from Step 1]
   NEXUS_ADMIN_EMAIL = superadmin@nexusai.in
   NEXUS_ADMIN_PASSWORD = [set a secure password, e.g., Render@Admin2025!]
   ```
6. Click **Create Web Service** — wait 3–5 minutes for deployment
7. Once deployed, you'll get a URL like: `https://nexus-ai-api.onrender.com`
8. **Copy this URL** — needed in Step 4

---

## Step 4: Deploy Frontend on Render

1. Go to https://dashboard.render.com
2. Click **New +** → **Static Site**
3. **Settings**:
   - Name: `nexus-ai-web`
   - **Build Command**: 
     ```bash
     cd frontend && npm install && npm run build
     ```
   - **Publish Directory**: `frontend/dist`
4. **Environment Variables** — add:
   ```
   VITE_API_URL = [paste your backend URL from Step 3, e.g., https://nexus-ai-api.onrender.com]
   ```
5. Click **Create Static Site** — wait 2–3 minutes
6. Once deployed, you'll get a URL like: `https://nexus-ai-web.onrender.com`

---

## Step 5: First Login

1. Open your frontend URL: `https://nexus-ai-web.onrender.com`
2. Log in as Super Admin:
   - **Email**: `superadmin@nexusai.in`
   - **Password**: [the one you set in Step 3]
3. You're live! 🎉

---

## What's Running Where

| Component | URL | Status | Tier |
|---|---|---|---|
| **Frontend** (React + Vite) | `https://nexus-ai-web.onrender.com` | Live | Free (static) |
| **Backend** (FastAPI) | `https://nexus-ai-api.onrender.com` | Live | Free (spins down idle) |
| **Database** (Postgres) | Neon Dashboard | Live | Free (10GB) |

---

## Important Notes

### Free Tier Limitations
- **Render Web Service** spins down after 15 minutes of inactivity (first request will be slow, 30s)
- **Render Static Site** is always fast (no spin-down)
- **Neon** free tier supports ~100,000 operations/month (plenty for a demo)

### To Keep Backend Awake
- Set up a simple uptime monitor (e.g., https://uptimerobot.com — free tier) to ping the backend every 10 min
- Or manually visit `/api/health` every 15 minutes to keep it warm

### Scale to Production
When ready to move beyond free tier:
1. Upgrade Render plan ($7–15/month for web service)
2. Upgrade Neon to paid tier ($15+/month for higher limits)
3. Use a proper domain name (point to Render)
4. Set up SSL/TLS (Render provides free SSL)

---

## Troubleshooting

**Backend won't deploy:**
- Check build logs in Render dashboard
- Verify `requirements.txt` is in repo root
- Ensure no syntax errors in `backend/main.py`

**Frontend won't build:**
- Verify `npm install` works locally first
- Check `frontend/package.json` exists
- Check `VITE_API_URL` is set correctly

**Database connection fails:**
- Verify Neon connection string is correct (should end with `?sslmode=require`)
- Check `DATABASE_URL` is set in Render environment variables
- Ensure Neon project is active (not paused)

---

## Next Steps After Deployment

1. **Test all features**: Register a company, upload CSVs, ask questions
2. **Share the link**: Give stakeholders `https://nexus-ai-web.onrender.com`
3. **Monitor**: Check Render dashboard for errors and performance
4. **Iterate**: Push updates to GitHub, Render auto-redeploys on `main` push
