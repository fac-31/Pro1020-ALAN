# Render Deployment Setup

## Important: CPU-Only PyTorch Installation

This project uses a custom build script to install CPU-only PyTorch, which saves ~500MB of memory compared to the CUDA version. This is critical for Render's free tier (512MB RAM).

## Configure Render to Use Build Script

In your Render dashboard:

1. Go to your Web Service settings
2. Under **Build Command**, set:
   ```bash
   ./backend/build.sh
   ```
   Or if Render runs from the backend directory:
   ```bash
   ./build.sh
   ```

3. Ensure **Root Directory** is set to:
   - If build runs from repo root: `backend/`
   - If build runs from backend: `.` (or leave empty)

4. **Start Command** should be:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

## What the Build Script Does

The `build.sh` script:
1. Installs PyTorch CPU-only version first (prevents CUDA version from being installed)
2. Then installs all other dependencies from `requirements.txt`
3. Saves ~500MB of memory (critical for 512MB free tier)

## Alternative: Manual Configuration

If you can't use the build script, you can manually set the build command in Render:

```bash
pip install torch==2.9.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu && pip install -r requirements.txt
```

## Verify CPU-Only PyTorch

After deployment, check logs to confirm CPU-only PyTorch was installed. You should see:
- PyTorch installation without CUDA libraries
- No `nvidia-*` packages in the installed packages list

## Troubleshooting

### "No open ports detected"
- The server now binds immediately, but if you still see this:
  - Check that services initialize in background (they should)
  - Verify the start command uses `$PORT` environment variable
  - Check server logs for startup errors

### Memory Issues
- Ensure CPU-only PyTorch is installed (check build logs)
- Enable `LOW_MEMORY_MODE=true` environment variable
- Check `rag_max_index_size` setting (default: 10000)

