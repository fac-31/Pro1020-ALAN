# Email Troubleshooting Guide

## Current Status (from Render)

✅ **Email Service**: Connected successfully to `hello.alan.01@gmail.com`  
⚠️ **Processed Messages**: 0 (either no emails received or polling not running)

## Diagnostic Steps

### 1. Check Render Logs

In your Render dashboard, look for these log messages:

**Good signs:**
- `"Email client initialized successfully"`
- `"Email polling task started with RAG integration"`
- `"Email polling task STARTED"` (with === lines around it)
- `"Checking for new emails..."`
- `"Found X unread emails"`

**Problem signs:**
- `"Email client not provided to polling task"`
- `"Failed to initialize email client"`
- `"Error in email polling task"`
- No "Checking for new emails..." messages

### 2. After Deploying New Code

Once you deploy the latest changes, you can use these endpoints:

**Check Email Status:**
```bash
curl https://pro1020-alan.onrender.com/email/status
```

**Manually Trigger Email Check:**
```bash
curl -X POST https://pro1020-alan.onrender.com/email/check
```

### 3. Verify Email Settings

Ensure these environment variables are set in Render:
- `GMAIL_USER=hello.alan.01@gmail.com` ✅ (confirmed working)
- `GMAIL_APP_PASS` (your Gmail app password)

**Polling Interval:**
- Default: 300 seconds (5 minutes)
- Set `POLLING_INTERVAL=60` for faster testing (1 minute)

### 4. Test Email Reception

1. Send an email to `hello.alan.01@gmail.com`
2. Wait for the polling interval (default 5 minutes)
3. Check Render logs for "Found X unread emails"
4. Check if a reply was sent

### 5. Common Issues

**Issue: Polling task not running**
- **Fix**: Check if email client initialization completed
- Check logs for any startup errors

**Issue: Emails found but no reply sent**
- Check logs for "Error processing email"
- Verify OpenAI API key is set correctly
- Check if reply generation is failing

**Issue: "Failed to establish IMAP connection"**
- Verify Gmail App Password is correct
- Check if IMAP is enabled in Gmail settings
- Verify Gmail account allows "Less secure app access" (if needed)

## Next Steps

1. **Deploy the latest code** with improved email diagnostics
2. **Check Render logs** for polling activity
3. **Test by sending an email** to `hello.alan.01@gmail.com`
4. **Use `/email/check` endpoint** after deployment to manually trigger checking

