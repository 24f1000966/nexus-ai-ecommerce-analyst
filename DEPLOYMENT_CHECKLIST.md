# Deployment Checklist — Nexus AI

Use this checklist to deploy to Render + Neon in 30 minutes.

## Pre-Deployment (5 min)

- [ ] Ensure repo is clean: `git status` shows no changes
- [ ] All code is pushed to GitHub: `git push origin main`
- [ ] Read [DEPLOYMENT.md](./DEPLOYMENT.md) once through
- [ ] Have browser tabs ready: 
  - https://neon.tech
  - https://render.com
  - https://github.com/24f1000966/nexus-ai-ecommerce-analyst

---

## Step 1: Neon Database Setup (5 min)

**Location**: https://neon.tech

1. [ ] Sign up or log in to Neon
2. [ ] Create new project → name: `nexus-ai`
3. [ ] Create database → name: `platform`
4. [ ] Go to **Connection String** → copy the PostgreSQL connection URL
5. [ ] **Paste it somewhere safe** — looks like: `postgresql://neondb_owner:xxxxx@ep-xxx.us-east-1.neon.tech/platform?sslmode=require`

---

## Step 2: Deploy Backend (8 min)

**Location**: https://render.com

1. [ ] Sign up or log in to Render
2. [ ] Click **New +** → **Web Service**
3. [ ] Select GitHub repository: `24f1000966/nexus-ai-ecommerce-analyst`
4. [ ] Fill in settings:
   - [ ] Service name: `nexus-ai-api`
   - [ ] Environment: `Python 3`
   - [ ] Build command: `pip install -r requirements.txt`
   - [ ] Start command: `uvicorn backend.main:api --host 0.0.0.0 --port 8000`
   - [ ] Plan: **Free**
5. [ ] Scroll down to **Environment Variables** and add:
   ```
   DATABASE_URL = [paste Neon connection string from Step 1]
   NEXUS_ADMIN_EMAIL = superadmin@nexusai.in
   NEXUS_ADMIN_PASSWORD = [create a strong password, e.g., Secure@Pass2025!]
   ```
6. [ ] Click **Create Web Service**
7. [ ] **Wait 3–5 minutes** for deployment to complete
8. [ ] Once done, copy the service URL (e.g., `https://nexus-ai-api.onrender.com`)
9. [ ] **Paste it in your notes** — needed for Step 3

---

## Step 3: Deploy Frontend (8 min)

**Location**: https://render.com (same dashboard)

1. [ ] Click **New +** → **Static Site**
2. [ ] Select GitHub repository: `24f1000966/nexus-ai-ecommerce-analyst`
3. [ ] Fill in settings:
   - [ ] Service name: `nexus-ai-web`
   - [ ] Build command: `cd frontend && npm install && npm run build`
   - [ ] Publish directory: `frontend/dist`
   - [ ] Plan: **Free**
4. [ ] Scroll down to **Environment Variables** and add:
   ```
   VITE_API_URL = [paste backend URL from Step 2, e.g., https://nexus-ai-api.onrender.com]
   ```
5. [ ] Click **Create Static Site**
6. [ ] **Wait 2–3 minutes** for deployment to complete
7. [ ] Copy the service URL (e.g., `https://nexus-ai-web.onrender.com`)

---

## Step 4: Verify Deployment (3 min)

1. [ ] Open your frontend URL in a browser: `https://nexus-ai-web.onrender.com`
2. [ ] You should see the Nexus AI login page
3. [ ] Log in with:
   - Email: `superadmin@nexusai.in`
   - Password: [the one you set in Step 2]
4. [ ] You should see the Super Admin dashboard ✓

---

## Step 5: Post-Deployment Testing (5 min)

**Optional but recommended:**

1. [ ] Test Register: Go to `/register`, sign up a test company (all fields)
2. [ ] Test Approval: As Super Admin, approve the company from **Companies** tab
3. [ ] Test Upload: Log in as the company, go to **Data** tab, upload a CSV (use `trial-data/sample-company-data/customers.csv`)
4. [ ] Test Question: Go to **Analyst** tab, ask "Who are the top customers?"
5. [ ] Test Health: As Super Admin, view **Platform Health** strip

---

## Troubleshooting

| Problem | Solution |
|---|---|
| **Backend won't deploy** | Check build logs in Render → dashboard. Verify `requirements.txt` exists in root. |
| **Frontend build fails** | Ensure `VITE_API_URL` is set (must include protocol: `https://...`). Check frontend logs. |
| **Can't log in** | Verify `NEXUS_ADMIN_PASSWORD` matches what you set in Step 2. Check browser console for errors. |
| **Blank page / 404** | Ensure `VITE_API_URL` points to backend URL from Step 2. Wait for static site to fully deploy. |
| **Slow first request** | Normal — free Render web service spins down. First request takes ~30s. Subsequent requests are instant. |

---

## Success! 🎉

Your project is now **live** and **shareable**:
- **Frontend**: `https://nexus-ai-web.onrender.com`
- **Backend API**: `https://nexus-ai-api.onrender.com`
- **Database**: Neon (managed)

**Share these links** with your project stakeholders, professors, or the PPD II team.

---

## To Keep Backend "Awake" (Optional)

The free Render web service spins down after 15 min of inactivity. To keep it responsive:

**Option A: Use Uptime Robot (Free)**
1. Go to https://uptimerobot.com
2. Create a free account
3. Add monitor: `https://nexus-ai-api.onrender.com/api/health`
4. Set interval to 10 minutes
5. Backend will stay warm 24/7

**Option B: Manual Ping**
- Visit `https://nexus-ai-api.onrender.com/api/health` every 15 min (or have a browser tab open)

---

## Next: Push Updates

When you make code changes:
1. Commit and push to GitHub: `git push origin main`
2. Render **auto-redeploys** within 1–2 minutes
3. No manual intervention needed

---

## Questions?

Refer to **[DEPLOYMENT.md](./DEPLOYMENT.md)** for detailed explanations and troubleshooting steps.
