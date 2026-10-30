# 🍎 Eclipse Shield - macOS Quick Start Guide

## 🚀 Get Started in 3 Steps

### 1. Install & Setup
```bash
# Make sure Docker Desktop is running
./install-local.sh
```

### 2. Add Your API Key (optional)
```bash
# Edit with your Google Generative AI API key
nano api_key.txt
```
Without a key, Eclipse Shield runs in local rules-only mode: allow and block lists, category rules, and context matching still work. Check which mode is active at `http://localhost:5000/health` (the `ai` field).

### 3. Start Eclipse Shield
```bash
./start.sh
```

**🌐 Access at: http://localhost:5000**

---

## 📋 Daily Usage

### Start/Stop Commands
```bash
./start.sh    # Start Eclipse Shield
./stop.sh     # Stop Eclipse Shield
./status.sh   # Check if running
```

### Monitoring
```bash
./logs.sh     # View live logs
./test.sh     # Run security tests
```

### Quick Health Check
```bash
curl http://localhost:5000/health
```

---

## 🔧 Customization

### Domain Settings (`settings.json`)
Configure what sites are allowed/blocked:

```json
{
  "domains": {
    "work": {
      "allowed_platforms": {
        "productivity": ["google.com", "notion.so"],
        "development": ["github.com", "stackoverflow.com"],
        "ai_tools": ["chat.openai.com", "claude.ai"]
      },
      "blocked_specific": ["facebook.com", "twitter.com"],
      "blocked_keywords": ["game", "entertainment"]
    }
  }
}
```

### Environment Settings (`.env.local`)
- Automatically generated with secure defaults
- Contains secret keys and configuration
- Keep this file secure!

---

## 🔌 Chrome Extension

1. **Open Chrome Extensions**: `chrome://extensions/`
2. **Enable Developer Mode**: Toggle in top-right
3. **Load Unpacked**: Select the `extension/` folder
4. **Configure**: Extension will connect to `http://localhost:5000`

---

## 🛠️ Troubleshooting

### Problem: Port 5000 already in use
```bash
lsof -ti:5000 | xargs kill -9  # Kill processes on port
./start.sh                     # Start again
```

### Problem: Docker not running
```bash
open -a Docker    # Start Docker Desktop
# Wait for startup, then try ./start.sh again
```

### Problem: Permission denied
```bash
chmod +x *.sh     # Make scripts executable
```

### Problem: Can't access localhost:5000
```bash
./status.sh       # Check if services are running
./logs.sh         # Check for errors
```

---

## 🔒 Security Features Active

✅ **Docker Isolation**: App runs in secure container  
✅ **Input Validation**: All URLs/domains validated  
✅ **Rate Limiting**: Prevents abuse  
✅ **Session Security**: Redis-backed sessions  
✅ **CORS Protection**: Chrome extension ready  
✅ **Security Headers**: XSS/clickjacking protection  
✅ **Non-root Execution**: Container security  

---

## 📊 Key URLs

| Purpose | URL |
|---------|-----|
| Main App | http://localhost:5000 |
| Health Check | http://localhost:5000/health |
| Block Page | http://localhost:5000/block.html |
| Extension Assets | http://localhost:5000/extension/ |

---

## 💡 Pro Tips

- **Background Running**: Eclipse Shield runs in Docker containers
- **Automatic Restart**: Containers restart if they crash
- **Log Monitoring**: Use `./logs.sh` to debug issues
- **Regular Testing**: Run `./test.sh` to verify security
- **Updates**: `git pull` then rebuild containers

---

## 🆘 Need Help?

1. **Check Status**: `./status.sh`
2. **View Logs**: `./logs.sh`
3. **Test Security**: `./test.sh`
4. **Restart Clean**: `./stop.sh && ./start.sh`

**🛡️ Your Eclipse Shield is ready to keep you productive and secure!**
