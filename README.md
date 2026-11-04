![Banner: the eclipse shield at full span, distracting app windows bouncing off its corona while the desk below stays calm and lit](banner.png)

# Eclipse Shield <img src="logo.png" alt="Eclipse Shield logo: a black eclipse disc with a gold corona curving into a shield" width="48">

**The Corona Shield**
_A black eclipse hangs over the desk, its gold corona bent into a shield, and every glowing distraction breaks against it and falls away._

**AI-powered productivity analyzer that helps users stay focused by blocking unproductive websites and providing contextual task guidance.**

![macOS](https://img.shields.io/badge/macOS-10.15%2B-blue?style=flat-square)
![License](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square)

Eclipse Shield uses artificial intelligence to understand your current work context and dynamically blocks distracting websites while asking intelligent questions to keep you on track with your goals.

![Scene: the corona shield, its rays pulsing while stray windows drift in and rebound](assets-scene.svg)

![Major separator](sep-heavy.svg)

---

## 🎩 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [✨ Features](#-features)
- [⚙️ Configuration](#️-configuration)
- [🏗️ How It Works](#️-how-it-works)
- [📋 Requirements](#-requirements)
- [🔒 Security](#-security)
- [📖 Documentation](#-documentation)
- [🤝 Contributing](#-contributing)

---

## 🚀 Quick Start

> [!WARNING]
> The browser extension asks Chrome or Opera for access to the sites you visit: `extension/manifest.json` lists host permissions for all URLs, plus the tabs and web navigation permissions. It needs that access so each visit can be sent to the Eclipse Shield backend running on your own machine at http://localhost:5000 and checked against your context and rules. Eclipse Shield does not ask macOS for Screen Recording or Accessibility permissions.

> **Under the corona, in plain words.** Set the context in plain words first, then let each visit be judged against it, in the order the Security entry logs.


**For macOS users (recommended):**

1. **Read the [QUICKSTART.md](QUICKSTART.md) guide** - Complete setup in 3 simple steps
2. **Run the installer**: `./install-local.sh`
3. **Optional: add a Google Gemini API key** from [Google AI Studio](https://aistudio.google.com/), either in `api_key.txt` or as the `GOOGLE_API_KEY` environment variable

**Without Docker, on any platform:**

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-secure.txt
python3 secure_app.py        # serves http://localhost:5000
curl http://localhost:5000/health
```

**For other platforms or advanced setup:**
- [Installation Guide](docs/INSTALLATION.md)
- [Production Deployment](docs/DEPLOYMENT.md)

---

![Major separator](sep-heavy.svg)

## ✨ Features

| Feature | What it does | Why it matters |
|---|---|---|
| Contextual Understanding | AI analyzes your current task and goals | Blocking decisions follow the work you are doing, not a fixed list alone |
| Smart Blocking | Dynamic website filtering based on work context | Sites that fight your current context are filtered while you work |
| Adaptive Questions | Intelligent prompts to maintain focus | The app checks your intent instead of guessing silently |
| Cross-Platform Extensions | Chrome and Opera support | The same blocking works in either supported browser |
| Real-Time Communication | Secure messaging between browser and backend | The extension and the local backend stay in step on every visit |
| Smooth Blocking | Instant website filtering without page refreshes | A blocked site is stopped at once, without a reload cycle |
| OWASP Top 10 Compliance | Complete security framework implementation | The backend is built against a known security checklist |
| Multi-Layer Defense | Firewall, intrusion detection, and application security | More than one layer has to fail before the app is exposed |
| Production Ready | Automated deployment with security hardening | The same setup can move from a laptop to a server |

---

## ⚙️ Configuration

- **Domain profiles (`settings.json`)**: Each profile (for example work or school) carries its own allowed platforms, `blocked_specific` sites, `blocked_keywords`, and blocked categories. Edit the profile that matches the context you are working in.
- **API key (optional)**: Add a Google Gemini API key from [Google AI Studio](https://aistudio.google.com/) in `api_key.txt` or as the `GOOGLE_API_KEY` environment variable. The key enables AI decisions for sites that match no explicit rule.
- **Without a key**: The analyzer runs in local rules-only mode: explicit allow and block lists, category rules, and context matching still work, and the `/health` endpoint reports `"ai": "local-only"`.
- **Full guide**: See the [Configuration Guide](docs/CONFIGURATION.md) for the remaining settings.

---

## 🏗️ How It Works

1. **Setup Your Context**: Define your work domains and productivity goals
2. **AI Learning**: Eclipse Shield asks contextual questions about your current task
3. **Smart Filtering**: Based on your responses, the AI determines which sites support your goals
4. **Dynamic Blocking**: Unproductive websites are blocked in real-time
5. **Continuous Adaptation**: The system learns and improves its decisions over time
6. **Flexible Configuration**: Customize rules and contexts for different work scenarios

---

## 📋 Requirements

### Minimum Requirements
- **Python 3.8+**
- **Modern web browser** (Chrome or Opera)
- **Google Gemini API key** (optional, free tier available): enables AI decisions for sites that match no explicit rule. Without a key the analyzer runs in local rules-only mode: explicit allow and block lists, category rules, and context matching still work, and the `/health` endpoint reports `"ai": "local-only"`.

### For Production Use
- **Redis** (for rate limiting and caching)
- **Nginx** (reverse proxy)
- **Docker** (containerized deployment)

See [System Requirements](docs/REQUIREMENTS.md) for detailed specifications.

---

![Minor separator](sep-light.svg)

## 🔒 Security

Eclipse Shield implements comprehensive security measures:

- ✅ **Input Validation**: Prevents injection attacks and malicious inputs
- ✅ **Rate Limiting**: Protects against abuse and DDoS attacks  
- ✅ **Secure Authentication**: API key management and CSRF protection
- ✅ **Privacy Protection**: Local processing with encrypted communications

For detailed security information, see [SECURITY.md](SECURITY.md).

**Run Security Tests** (with the server running):
```bash
python3 security_test.py http://localhost:5000
```

**Run the automated test suite** (no server or API key needed):
```bash
python3 -m pytest tests/ -q
```

---

## 📖 Documentation

### User Guides
- [🍎 macOS Quick Start](QUICKSTART.md) - Get started in 3 steps
- [⚙️ Configuration Guide](docs/CONFIGURATION.md) - Customize your settings
- [🔧 Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

### Technical Documentation
- [🏗️ Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions
- [🚀 Deployment Guide](docs/DEPLOYMENT.md) - Production deployment
- [🔌 API Reference](docs/API.md) - API endpoints and usage
- [🏛️ Architecture](docs/ARCHITECTURE.md) - System design and components

### Security & Operations
- [🛡️ Security Guide](SECURITY.md) - Comprehensive security documentation
- [📊 Monitoring](docs/MONITORING.md) - Logging and performance monitoring
- [🔄 Backup & Recovery](docs/BACKUP.md) - Data protection procedures

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Links
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Issue Templates](.github/ISSUE_TEMPLATE/)
- [Development Setup](docs/DEVELOPMENT.md)

---

## 📄 License

This project is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International License](LICENSE).

---

## 🆘 Need Help?

- **Quick Issues**: Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Documentation**: Browse the [docs/](docs/) folder
- **Bug Reports**: Use our [issue tracker](../../issues)
- **Security Issues**: See [SECURITY.md](SECURITY.md) for reporting procedures

---

*Eclipse Shield - Stay focused, stay productive* 🎯

---

![Intro: a worker at a desk at night, the eclipse shield hanging in the sky above, its gold corona turning aside a rain of glowing app windows](intro-banner.png)

## Diagrams and maps

I drew the system out in [Eclipse-Shield-Visuals](Eclipse-Shield-Visuals/): an architecture diagram, a component map, a flowchart of one navigation, and a product map, with the written product map, statistics with citations, and the roadmap in [VISUAL.md](Eclipse-Shield-Visuals/VISUAL.md). Every sheet also ships as a PNG photograph of the paper page beside its SVG.

![Eclipse Shield architecture](Eclipse-Shield-Visuals/architecture.svg)