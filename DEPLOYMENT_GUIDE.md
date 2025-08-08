# 🚀 Production Deployment Guide
**Trading Bot Application - Render + Netlify Architecture**

## 📋 Architecture Overview

```
┌─────────────────┐    HTTP/WS     ┌─────────────────┐
│   Frontend      │◄──────────────►│    Backend      │
│   (Netlify)     │   API Calls    │    (Render)     │
│   React SPA     │                │   FastAPI       │
└─────────────────┘                └─────────────────┘
         │                                   │
         │                                   │
         ▼                                   ▼
┌─────────────────┐                ┌─────────────────┐
│   CDN/Static    │                │   PostgreSQL    │
│   Assets        │                │   Database      │
└─────────────────┘                └─────────────────┘
```

**Components:**
- **Frontend**: React SPA deployed on Netlify
- **Backend**: FastAPI Python app deployed on Render
- **Database**: PostgreSQL (Render-managed or external)
- **Monitoring**: Prometheus + Grafana (optional Docker setup)

## 🔐 Required Secrets & Environment Variables

### GitHub Secrets (Repository Settings > Secrets)

#### Backend (Render) Secrets:
```bash
# Render deployment
RENDER_API_KEY=your-render-api-key
RENDER_SERVICE_ID=your-render-service-id

# Database
DATABASE_URL=postgresql://user:password@host:port/database

# JWT & Security
JWT_SECRET_KEY=your-super-secure-jwt-secret-at-least-32-chars

# Broker APIs
UPSTOX_API_KEY=your-upstox-api-key
UPSTOX_API_SECRET=your-upstox-secret
UPSTOX_MOBILE=your-mobile-number
UPSTOX_PIN=your-6-digit-pin
UPSTOX_TOTP_KEY=your-totp-secret

# Add other broker credentials similarly...
ANGEL_ONE_API_KEY=your-angel-api-key
DHAN_CLIENT_ID=your-dhan-client-id
# ... etc

# Backup & Monitoring
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
BACKUP_S3_BUCKET=your-backup-bucket
```

#### Frontend (Netlify) Secrets:
```bash
# Netlify deployment
NETLIFY_AUTH_TOKEN=your-netlify-auth-token
NETLIFY_SITE_ID=your-netlify-site-id

# API connection (point to your Render backend)
REACT_APP_API_URL=https://your-backend.onrender.com
REACT_APP_WS_URL=wss://your-backend.onrender.com

# Optional: Staging URLs for PR previews
REACT_APP_API_URL_STAGING=https://your-backend-staging.onrender.com
REACT_APP_WS_URL_STAGING=wss://your-backend-staging.onrender.com
```

## 🎯 Step-by-Step Deployment Setup

### 1. Backend Deployment (Render)

1. **Create Render Account**: Go to [render.com](https://render.com)

2. **Create New Web Service**:
   - Connect your GitHub repository
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `./start.sh`
   - **Environment**: `Python 3.10+`

3. **Configure Environment Variables** in Render Dashboard:
   ```bash
   DATABASE_URL=postgresql://...
   JWT_SECRET_KEY=your-secret-key
   UPSTOX_API_KEY=your-api-key
   UPSTOX_API_SECRET=your-api-secret
   UPSTOX_MOBILE=your-mobile
   UPSTOX_PIN=your-pin
   UPSTOX_TOTP_KEY=your-totp-key
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   REDIS_ENABLED=false  # Or configure Redis if needed
   ```

4. **Database Setup**:
   - Create PostgreSQL instance in Render
   - Copy DATABASE_URL to environment variables
   - Database migrations will run automatically via `start.sh`

### 2. Frontend Deployment (Netlify)

1. **Create Netlify Account**: Go to [netlify.com](https://netlify.com)

2. **Create New Site**:
   - Connect your GitHub repository
   - **Base directory**: `ui/trading-bot-ui`
   - **Build command**: `npm run build`
   - **Publish directory**: `build`

3. **Configure Environment Variables** in Netlify:
   ```bash
   REACT_APP_API_URL=https://your-backend.onrender.com
   REACT_APP_WS_URL=wss://your-backend.onrender.com
   GENERATE_SOURCEMAP=false
   ```

4. **Domain Setup** (Optional):
   - Add custom domain in Netlify dashboard
   - Configure DNS to point to Netlify
   - SSL certificate will be auto-generated

### 3. GitHub Actions Setup

1. **Add Repository Secrets**:
   - Go to GitHub repo → Settings → Secrets and Variables → Actions
   - Add all the secrets listed above

2. **Configure Render API Key**:
   ```bash
   # Get from Render Dashboard → Account Settings → API Keys
   RENDER_API_KEY=rnd_xxxxxxxxxxxxxxxxxxxxx
   ```

3. **Configure Netlify Tokens**:
   ```bash
   # Get from Netlify Dashboard → User Settings → Applications → OAuth
   NETLIFY_AUTH_TOKEN=your-netlify-token
   NETLIFY_SITE_ID=your-site-id  # From site settings
   ```

## 🔧 Configuration Files Update

### 1. Update API URLs in Frontend

Edit `ui/trading-bot-ui/public/_redirects`:
```bash
# Replace with your actual Render backend URL
/api/*  https://your-actual-backend.onrender.com/api/:splat  200
/*    /index.html   200
```

### 2. CORS Configuration

In your FastAPI backend (`app.py`), ensure CORS is configured for Netlify:
```python
from fastapi.middleware.cors import CORSMiddleware

# Add your Netlify domain
origins = [
    "https://your-frontend.netlify.app",
    "https://your-custom-domain.com",  # If using custom domain
    "http://localhost:3000",  # For local development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🚀 Deployment Process

### Automatic Deployments

1. **Push to `main` branch**:
   ```bash
   git add .
   git commit -m "feat: deploy to production"
   git push origin main
   ```

2. **GitHub Actions will**:
   - Run backend tests and security scans
   - Deploy backend to Render
   - Run frontend tests and builds
   - Deploy frontend to Netlify
   - Run post-deployment health checks

### Manual Deployments

1. **Backend (Render)**:
   - Go to Render dashboard
   - Click "Manual Deploy" → "Deploy latest commit"

2. **Frontend (Netlify)**:
   - Go to Netlify dashboard
   - Click "Trigger Deploy" → "Deploy site"

## 📊 Monitoring & Health Checks

### 1. Health Check Endpoints

- **Backend Health**: `https://your-backend.onrender.com/health`
- **API Status**: `https://your-backend.onrender.com/api/v1/status`

### 2. Monitoring Setup (Optional)

Deploy monitoring stack using `docker-compose.monitoring.yml`:
```bash
# On a separate server or cloud instance
docker-compose -f docker-compose.monitoring.yml up -d
```

Access dashboards:
- **Grafana**: `http://your-monitoring-server:3001`
- **Prometheus**: `http://your-monitoring-server:9090`

## 🔍 Troubleshooting

### Common Issues & Solutions

1. **Frontend can't connect to backend**:
   - Check `REACT_APP_API_URL` in Netlify environment
   - Verify CORS configuration in FastAPI
   - Check network connectivity

2. **Playwright automation fails on Render**:
   - Ensure `start.sh` installs Playwright correctly
   - Check memory usage (Render limit: 500MB)
   - Verify browser args in production config

3. **Database connection issues**:
   - Verify `DATABASE_URL` format
   - Check PostgreSQL instance status in Render
   - Test connection from backend logs

4. **WebSocket connections fail**:
   - Ensure WebSocket URL uses `wss://` (not `ws://`)
   - Check if proxy/CDN supports WebSockets
   - Verify WebSocket handlers are configured

5. **Build failures**:
   - Check build logs in respective platforms
   - Verify all dependencies are in requirements.txt/package.json
   - Check for memory/timeout issues during build

### Debug Commands

```bash
# Test backend health
curl https://your-backend.onrender.com/health

# Test API endpoint
curl https://your-backend.onrender.com/api/v1/status

# Check frontend build
cd ui/trading-bot-ui && npm run build

# Test WebSocket connection
wscat -c wss://your-backend.onrender.com/ws
```

## 🔐 Security Checklist

- [ ] All API keys stored as environment variables (not in code)
- [ ] HTTPS enabled on both frontend and backend
- [ ] CORS properly configured
- [ ] Security headers configured (see `_headers` file)
- [ ] Database connections encrypted
- [ ] JWT secrets are strong (32+ characters)
- [ ] Regular security updates via Dependabot
- [ ] Rate limiting enabled on API endpoints

## 📈 Performance Optimization

### Backend (Render)
- Use Render's auto-scaling features
- Enable Redis for caching (if needed)
- Optimize database queries
- Monitor memory usage (500MB limit)

### Frontend (Netlify)
- Leverage Netlify's global CDN
- Enable build optimizations (minification, compression)
- Use lazy loading for large components
- Implement proper caching headers

## 🎯 Cost Optimization

### Render (Backend)
- **Starter Plan**: $7/month (512MB RAM)
- **Standard Plan**: $25/month (2GB RAM) - Recommended for production
- **Database**: $7/month (PostgreSQL)

### Netlify (Frontend)
- **Free Tier**: 100GB bandwidth/month
- **Pro Plan**: $19/month (400GB bandwidth) - For heavy usage

**Total Estimated Cost**: ~$32-51/month for production setup

---

## 🆘 Support & Documentation

- **Render Docs**: [render.com/docs](https://render.com/docs)
- **Netlify Docs**: [docs.netlify.com](https://docs.netlify.com)
- **FastAPI Docs**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **GitHub Actions**: [docs.github.com/actions](https://docs.github.com/en/actions)

**Your production trading application is now ready for deployment! 🚀📈**