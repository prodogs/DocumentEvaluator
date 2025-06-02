# Server Startup Instructions

## ⚠️ IMPORTANT: Single Entry Point

**ALWAYS use `app.py` as the ONLY entry point for the server.**

## How to Start the Server

```bash
cd server
source ../venv/bin/activate
python app.py
```

## What Was Fixed

Previously, there were TWO files causing confusion:
- ❌ `app.py` - Had incomplete route registration (caused 404 errors)
- ❌ `app_launcher.py` - Had complete route registration but was confusing

**Solution:** Consolidated everything into `app.py` and deleted `app_launcher.py`

## Current Status

✅ **`app.py`** - Complete, consolidated entry point with:
- All route registrations
- Swagger UI configuration
- Service initialization
- Health monitoring
- Background services
- Proper logging

❌ **`app_launcher.py`** - DELETED to prevent confusion

## Never Again

- Only run `python app.py` 
- Never create another launcher file
- All routes and services are in `app.py`
- If you see 404 errors, check that you're running `app.py` not some other file

## Verification

The server should show:
- ✅ All 100+ routes registered
- ✅ Health check at `/api/health` returns `{"status": "ok"}`
- ✅ Swagger UI at `/api/docs`
- ✅ Batch management routes working
- ✅ No 404 errors for API endpoints
