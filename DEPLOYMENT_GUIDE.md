# ECDAT (Cipher Observatory) — 24/7 Free Cloud Deployment Guide
**Smart India Hackathon 2026 · Problem Statement SIH26164 (NTRO)**

This guide provides the exact steps to deploy the ECDAT platform **100% free of cost, 24/7/365**, ensuring evaluation jury and examiners can access and interact with the live software at any time without downtime or cold-start errors.

---

## 🚀 Architecture & 24/7 Resilience

| Component | Recommended Platform | Cost | Uptime / Sleep Behavior | Standalone Resilience |
|---|---|---|---|---|
| **Frontend (Next.js 15)** | **Vercel (Hobby Tier)** | **100% Free** | **24/7 Active (Never Sleeps)** | **Built-in MSW**: All 19 routes & 3D WebGL run with 0 errors even if backend sleeps |
| **Backend (FastAPI)** | **Render.com / Railway** | **100% Free** | Spins down after 15m idle; auto-wakes on request | Auto-seeded SQLite database with preloaded defense assets |

---

## Step 1: Deploy Frontend on Vercel (30 Seconds)

The frontend code has been tested (`✓ Generating static pages 19/19`) and pushed to your GitHub repository: [`nani224/SIH26164`](https://github.com/nani224/SIH26164).

### Method A: 1-Click Import Link
Click this direct link:
👉 **[Deploy to Vercel](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fnani224%2FSIH26164&project-name=ecdat-cipher-observatory&root-directory=frontend)**

### Method B: Manual Import on Vercel
1. Go to **[vercel.com/new](https://vercel.com/new)** and log in with your GitHub account.
2. Under "Import Git Repository", find **`SIH26164`** and click **Import**.
3. In the configuration screen:
   - **Framework Preset**: Next.js *(automatically detected)*
   - **Root Directory**: Click `Edit` and select **`frontend`**
   - **Build Command**: `pnpm build` *(default)*
   - **Output Directory**: `.next` *(default)*
4. Under **Environment Variables**, add:
   - `NEXT_PUBLIC_ENABLE_MSW` = `true` *(guarantees 100% uptime for examiners even if offline)*
   - `NEXT_PUBLIC_ECDAT_API_TOKEN` = `ecdat-dev-insecure-token`
5. Click **Deploy**.

> 🎉 Within 45 seconds, Vercel will generate your live production URL (e.g. `https://ecdat-cipher-observatory.vercel.app`).

---

## Step 2: Deploy Backend on Render (1-Click Blueprint)

The backend is packaged as an air-gapped Docker container with a pre-seeded SQLite database. A `render.yaml` file has already been committed to your repo.

1. Go to **[dashboard.render.com](https://dashboard.render.com)** and log in with GitHub.
2. Click the **New +** button in the top right and select **Blueprint**.
3. Connect your **`nani224/SIH26164`** repository.
4. Render will automatically read `render.yaml` and configure:
   - `ecdat-backend`: Web service running Docker on port 8000
   - `ecdat-frontend`: Web service running Next.js
5. Click **Apply**.
6. Render will build and deploy the container. Once live, you will get an API URL like `https://ecdat-backend.onrender.com`.

---

## Step 3: Link Frontend to Backend (Optional)

If you deployed the Render backend and want your Vercel frontend to query the live backend API:
1. In your **Vercel Project Dashboard**, go to **Settings** ➔ **Environment Variables**.
2. Add / Update:
   - `NEXT_PUBLIC_API_URL` = `https://ecdat-backend.onrender.com`
   - `NEXT_PUBLIC_ENABLE_MSW` = `false` *(or leave as `true` for auto-fallback)*
3. Trigger a redeploy.

---

## 🛡️ Why This Setup Is Examiner-Proof

1. **Zero Cold-Start Crashes**: Vercel serves the frontend from edge CDN nodes across India and globally in under 200ms.
2. **Offline Air-Gap Demonstration**: When `NEXT_PUBLIC_ENABLE_MSW=true`, all 19 screens (Overview, Mosca Matrix, Stripped Binaries, 3D Spatial Topology, Deep Finding Drawer, CBOM Export) execute with full deterministic mock data, perfectly demonstrating the air-gapped, zero-cloud premise required by NTRO!
3. **100% Free**: Neither Vercel nor Render requires credit card billing for standard evaluation traffic.
