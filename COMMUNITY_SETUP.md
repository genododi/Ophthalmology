# Community Submissions Setup Guide

This guide explains how to set up the community submissions feature for your Ophthalmic Infographic Creator GitHub Pages site.

## Overview

The community feature allows:
- Users to submit their generated infographics to a public pool
- Other users to view, like, and download community infographics
- Administrators to approve or reject submissions
- All without requiring a traditional database

## Architecture

Since GitHub Pages is static hosting, we use **JSONBin.io** as a free JSON storage service to store submissions. This allows:
- Read/write operations from the browser
- No backend server needed
- Free tier: 10,000 requests/month

## Setup Instructions

### Step 1: Create a JSONBin.io Account

1. Go to [https://jsonbin.io](https://jsonbin.io)
2. Click "Sign Up" and create a free account
3. Verify your email if required

### Step 2: Create a Storage Bin

1. After logging in, click "Create Bin" or go to Dashboard
2. In the editor, paste this initial JSON structure:

```json
{
  "submissions": [],
  "approved": []
}
```

3. Click "Create" to save the bin
4. Copy the **Bin ID** from the URL (it looks like `60a7b8c9d1234e56789abcdef`)

### Step 3: Get Your API Keys

1. Go to your JSONBin.io dashboard
2. Click on "API Keys" in the sidebar
3. Copy your **Master Key** (starts with `$2a$10$...`)
4. Optionally create an **Access Key** for read-only operations

### Step 4: Configure the Application

1. Open `community-submissions.js` in your repository
2. Find the `JSONBIN_CONFIG` object near the top:

```javascript
const JSONBIN_CONFIG = {
    BIN_ID: 'YOUR_BIN_ID_HERE',
    MASTER_KEY: '$2a$10$YOUR_MASTER_KEY_HERE',
    ACCESS_KEY: '$2a$10$YOUR_ACCESS_KEY_HERE',
    BASE_URL: 'https://api.jsonbin.io/v3/b'
};
```

3. Replace the placeholder values with your actual credentials:
   - `BIN_ID`: Your bin ID from Step 2
   - `MASTER_KEY`: Your master key from Step 3
   - `ACCESS_KEY`: Your access key (optional, can be same as master key)

### Step 5: Set Admin PIN

1. In `community-submissions.js`, find the `ADMIN_PIN` constant:

```javascript
const ADMIN_PIN = '1234';
```

2. Change `'1234'` to your preferred PIN (used for approval operations)

### Step 6: Deploy to GitHub Pages

1. Commit and push all changes to your repository
2. Wait for GitHub Pages to rebuild (usually 1-2 minutes)
3. Your community features should now be active!

## How It Works

### For Users

1. **Generate an infographic** using the main creator
2. Click the **"Submit to Community"** button (group_add icon) in the toolbar
3. Enter your name and confirm submission
4. Your infographic appears in the **Community Hub** pending approval

### For Other Users

1. Click the **"Community Hub"** button (groups icon) in the toolbar
2. Browse pending and approved infographics
3. **Like** infographics you find helpful
4. **Download** infographics to your local library

### For Administrators

1. Go to `your-site.github.io/ophthalmology/moderation.html`
2. Enter your admin PIN to unlock
3. Review pending submissions with full metadata:
   - User name
   - Submission date
   - Infographic title
   - User IP address
   - Like count
4. **Approve** to move to public gallery or **Reject** to remove

## Security Considerations

⚠️ **Important Notes:**

1. **API Keys**: The master key is visible in client-side code. For production, consider:
   - Using a serverless function (Cloudflare Workers, Netlify Functions) as a proxy
   - Creating read-only access keys for public operations
   
2. **Admin PIN**: This is basic security. For sensitive applications, implement proper authentication.

3. **Rate Limiting**: JSONBin.io free tier has limits. Monitor usage if your site gets high traffic.

4. **Data Privacy**: IP addresses are collected for moderation. Ensure your privacy policy reflects this.

## Demo Mode

If JSONBin is not configured, the system automatically falls back to **localStorage demo mode**:
- Submissions are stored locally in the browser
- Only visible to the current user
- Useful for testing before full deployment

## File Structure

```
ophthalmology/
├── index.html              # Main application (Community Hub modals added)
├── script.js               # Main JS (Community Hub setup added)
├── style.css               # Styles (Community styles added)
├── community-submissions.js # Community module (JSONBin integration)
├── moderation.html         # Admin moderation panel
└── COMMUNITY_SETUP.md      # This setup guide
```

## Troubleshooting

### "Community module not loaded"
- Ensure `community-submissions.js` is loaded before `script.js` in index.html
- Check browser console for JavaScript errors

### "JSONBin not configured"
- Verify your BIN_ID and keys are correctly set
- Check that JSONBin.io is accessible from your network

### Submissions not appearing
- Check browser console for API errors
- Verify JSONBin.io is returning valid JSON
- Clear localStorage cache: `localStorage.removeItem('ophthalmic_community_cache')`

### Admin panel not working
- Ensure you're entering the correct PIN
- Check that the PIN in `community-submissions.js` matches what you're entering

## Support

For issues or feature requests, please open an issue on the GitHub repository.
