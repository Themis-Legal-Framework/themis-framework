# Quick Redeployment Guide

This guide will help you redeploy the Themis application with the latest bug fixes.

## The Fix

The DDA (Document Drafting Agent) was generating document metadata but failing to include the actual document text. This has been fixed in commit `9af1d26`.

## Option 1: Automated Script (Recommended)

Run the automated redeployment script:

```bash
cd /home/user/themis-framework
./redeploy.sh
```

This script will:
1. Show current deployment status
2. Stop old containers
3. Pull latest code from git
4. Rebuild Docker images with the new code
5. Start services
6. Verify the API is healthy
7. Show final status and access URLs

## Option 2: Manual Steps

If you prefer to run commands manually:

```bash
# 1. Navigate to project directory
cd /home/user/themis-framework

# 2. Stop current deployment
docker-compose down
# OR if using newer Docker:
docker compose down

# 3. Pull latest code
git pull origin claude/fix-garbage-output-011CUXuX4scspMjp45XDtXz5

# 4. Rebuild the API container (forces rebuild with new code)
docker-compose build --no-cache api
# OR:
docker compose build --no-cache api

# 5. Start services
docker-compose up -d
# OR:
docker compose up -d

# 6. Verify deployment
docker-compose ps
curl http://localhost:8000/health

# 7. View logs to confirm no errors
docker-compose logs -f themis-api
```

## Verification

After redeployment, verify the fix is working:

1. **Access the Themis UI**: http://localhost:8000/docs

2. **Test Document Generation**:
   - Submit a case through the web interface
   - The DDA agent should now generate complete documents with actual text
   - You should see the full complaint/motion/demand letter content
   - No more "Unable to generate complete document text" errors

3. **Check the Response JSON**:
   - Look for the `dda` section in the response
   - It should contain a `document` object with a `full_text` field
   - The `full_text` field should contain the actual legal document (not just metadata)

## Troubleshooting

### If the script fails:

**"Docker is not installed"**
- Install Docker: https://docs.docker.com/get-docker/

**"docker-compose not found"**
- Use `docker compose` (newer syntax) or install docker-compose

**"API health check timeout"**
```bash
# View logs to see what's wrong
docker-compose logs themis-api

# Check if API key is set
grep ANTHROPIC_API_KEY .env
```

**"Permission denied" on redeploy.sh**
```bash
chmod +x redeploy.sh
```

### If documents still don't generate:

1. Check API logs for errors:
```bash
docker-compose logs -f themis-api
```

2. Verify you're on the correct branch:
```bash
git branch
# Should show: * claude/fix-garbage-output-011CUXuX4scspMjp45XDtXz5
```

3. Confirm the fix is in the code:
```bash
git log --oneline -n 1
# Should show: 9af1d26 Fix DDA agent garbage output...
```

4. Check environment variables:
```bash
cat .env | grep ANTHROPIC_API_KEY
```

## Need Help?

If you continue to experience issues:
- Check logs: `docker-compose logs -f themis-api`
- View the detailed error in the API response JSON
- Open an issue with the full error message and logs
