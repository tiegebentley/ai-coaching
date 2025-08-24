# AI Coaching System - Deployment Guide

## ✅ Deployment Status
Your application is successfully deployed to Vercel! 

**Live URLs:**
- Production: `https://ai-coaching-git-main-secondbrains-projects-fbada7bc.vercel.app`
- Preview: `https://ai-coaching-n7qjtoj4j-secondbrains-projects-fbada7bc.vercel.app`

## 🔧 Required Environment Variables

To make your app fully functional, you need to add these environment variables in Vercel:

### Setting Environment Variables in Vercel

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Select your `ai-coaching` project
3. Go to **Settings** → **Environment Variables**
4. Add the following variables:

#### Required Variables:
```
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

#### Optional Variables:
```
NEXT_PUBLIC_API_BASE_URL=https://your-backend-api.com
NEXT_PUBLIC_ENVIRONMENT=production
```

### Getting Supabase Credentials

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Create a new project or select existing one
3. Go to **Settings** → **API**
4. Copy:
   - **Project URL** → Use as `NEXT_PUBLIC_SUPABASE_URL`
   - **Anon/Public Key** → Use as `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## 📝 What Was Fixed

### Build Issues Resolved:
1. ✅ Fixed `vercel.json` configuration to properly detect Next.js in frontend folder
2. ✅ Removed deprecated `appDir` from Next.js config
3. ✅ Fixed TypeScript errors with missing type annotations
4. ✅ Made Supabase client handle missing environment variables during build

### Files Modified:
- `vercel.json` - Proper build configuration for monorepo
- `frontend/next.config.js` - Removed deprecated experimental flag
- `frontend/src/lib/supabase.ts` - Graceful handling of missing env vars
- `frontend/src/hooks/useSupabase.ts` - Fixed TypeScript annotations
- `frontend/src/hooks/useEmailQueue.ts` - Fixed TypeScript annotations

## 🚀 Future Deployments

Any push to the `main` branch will automatically trigger a new deployment on Vercel.

### Local Development

```bash
# Frontend
cd frontend
npm install
npm run dev

# Backend
cd backend
pip install -r requirements.txt
python -m ai_coaching.main
```

## 🔒 Security Notes

- Never commit `.env` files to GitHub
- Always use environment variables for sensitive data
- Keep your Supabase keys secure
- Rotate keys periodically

## 📊 Monitoring

Check your deployment status at:
- [Vercel Dashboard](https://vercel.com/dashboard)
- View build logs for any issues
- Monitor function logs for API errors

## 🆘 Troubleshooting

### If the app shows errors after adding env vars:
1. Ensure variables are added to correct environment (Production/Preview/Development)
2. Trigger a redeployment from Vercel dashboard
3. Check browser console for specific error messages

### Common Issues:
- **404 Error**: Already fixed with proper `vercel.json` configuration
- **Missing Supabase Error**: Add environment variables as shown above
- **Build Failures**: All TypeScript errors have been fixed

## ✨ Next Steps

1. Add your Supabase credentials to Vercel
2. Set up your Supabase database tables (use migrations in `backend/src/ai_coaching/database/migrations/`)
3. Deploy your backend API separately
4. Update `NEXT_PUBLIC_API_BASE_URL` to point to your backend

Your app is ready for production use once environment variables are configured!