# Vercel Deployment Guide for Trade Surveillance Frontend

## Prerequisites
1. Vercel account (sign up at https://vercel.com)
2. GitHub account (if deploying from Git)
3. Backend API URL (Cloudflare tunnel or production URL)

## Step-by-Step Deployment

### Option 1: Deploy via Vercel CLI (Recommended)

#### Step 1: Install Vercel CLI
```bash
npm install -g vercel
```

#### Step 2: Login to Vercel
```bash
vercel login
```

#### Step 3: Navigate to Dashboard Directory
```bash
cd dashboard
```

#### Step 4: Deploy
```bash
vercel
```

Follow the prompts:
- Set up and deploy? **Yes**
- Which scope? (Select your account)
- Link to existing project? **No** (first time) or **Yes** (subsequent deployments)
- Project name? **trade-surveillance-frontend** (or your preferred name)
- Directory? **./** (current directory)
- Override settings? **No**

#### Step 5: Set Environment Variables
After first deployment, set environment variables:

```bash
vercel env add REACT_APP_API_URL
```

When prompted:
- **Value**: Enter your backend API URL (e.g., `https://backend.internal.tradesurveillance.in` or your Cloudflare tunnel URL)
- **Environment**: Select `production`, `preview`, and `development` (or just `production`)

Or set via Vercel Dashboard:
1. Go to your project on Vercel
2. Settings → Environment Variables
3. Add `REACT_APP_API_URL` with your backend URL

#### Step 6: Redeploy with Environment Variables
```bash
vercel --prod
```

---

### Option 2: Deploy via Vercel Dashboard (Git Integration)

#### Step 1: Push Code to GitHub
```bash
git add .
git commit -m "Prepare for Vercel deployment"
git push origin main
```

#### Step 2: Import Project in Vercel
1. Go to https://vercel.com/new
2. Click "Import Git Repository"
3. Select your repository
4. Configure project:
   - **Framework Preset**: Create React App
   - **Root Directory**: `dashboard`
   - **Build Command**: `npm run build`
   - **Output Directory**: `build`
   - **Install Command**: `npm install`

#### Step 3: Set Environment Variables
1. Go to Project Settings → Environment Variables
2. Add:
   - **Name**: `REACT_APP_API_URL`
   - **Value**: Your backend API URL (e.g., `https://backend.internal.tradesurveillance.in`)
   - **Environment**: Production, Preview, Development

#### Step 4: Deploy
Click "Deploy" button

---

## Environment Variables Required

| Variable | Description | Example |
|----------|-------------|---------|
| `REACT_APP_API_URL` | Backend API URL | `https://backend.internal.tradesurveillance.in` |

---

## Post-Deployment

### Update Backend CORS Settings
After deployment, update your backend's CORS configuration to allow your Vercel domain:

1. Get your Vercel deployment URL (e.g., `https://trade-surveillance-frontend.vercel.app`)
2. Update `CORS_ORIGINS` in backend `.env`:
   ```
   CORS_ORIGINS=https://trade-surveillance-frontend.vercel.app,https://your-custom-domain.com
   ```
3. Restart backend Docker container

### Custom Domain (Optional)
1. Go to Vercel Dashboard → Project → Settings → Domains
2. Add your custom domain
3. Follow DNS configuration instructions

---

## Troubleshooting

### Build Fails
- Check Node.js version (Vercel uses Node 18.x by default)
- Verify all dependencies are in `package.json`
- Check build logs in Vercel dashboard

### API Calls Fail (CORS Errors)
- Verify `REACT_APP_API_URL` is set correctly
- Check backend CORS settings include Vercel domain
- Check browser console for exact error

### Environment Variables Not Working
- Ensure variable name starts with `REACT_APP_`
- Redeploy after adding environment variables
- Check Vercel dashboard → Settings → Environment Variables

---

## Quick Commands

```bash
# Deploy to production
vercel --prod

# Deploy to preview
vercel

# View deployment logs
vercel logs

# List all deployments
vercel ls

# Remove deployment
vercel remove
```

