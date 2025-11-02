# 🚀 Quick Start

## 1. Installation

```bash
cd apuntador-oauth-backend

# Option A: Automatic script
./start.sh

# Option B: Manual
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configuration

```bash
# Create .env file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or your favorite editor
```

### Required variables:

```env
# Google Drive OAuth (required)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/oauth/callback/googledrive

# Dropbox OAuth (required)
DROPBOX_CLIENT_ID=your-dropbox-app-key
DROPBOX_CLIENT_SECRET=your-dropbox-app-secret  
DROPBOX_REDIRECT_URI=http://localhost:8000/api/oauth/callback/dropbox

# Secret key (change in production)
SECRET_KEY=generate-a-random-secret-key-here
```

## 3. Run

```bash
# Using Makefile
make dev

# Or directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 4. Test

Open your browser at:
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health**: http://localhost:8000/health

## 5. Integrate with client

See **[CLIENT_INTEGRATION.md](CLIENT_INTEGRATION.md)** for detailed instructions.

## Useful commands

```bash
make help         # View all available commands
make test         # Run tests
make lint         # Check code
make format       # Format code
make docker-build # Build Docker image
```

## Troubleshooting

### Error: "Import XXX could not be resolved"

Import errors you see in VSCode are normal before installing dependencies. Run:

```bash
pip install -r requirements.txt
```

### Error: "Google Drive OAuth not configured"

Make sure you have configured all variables in `.env`.

### Callback doesn't work

Verify that the redirect URI in Google Cloud Console matches exactly with the one in `.env`:
```
http://localhost:8000/api/oauth/callback/googledrive
```

## Next steps

1. ✅ Configure Google Drive OAuth in Google Cloud Console
2. ✅ Configure Dropbox OAuth in Dropbox App Console  
3. ✅ Run the backend (`make dev`)
4. ✅ Modify the Apuntador client to use the backend (see CLIENT_INTEGRATION.md)
5. ✅ Test the complete flow
6. ✅ Deploy to production (Railway/Render/Fly.io)
