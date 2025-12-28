# ShadowSpecter Menu Structure

## 📋 Complete Menu Bar Implementation

### 📁 FILE MENU
```
├── 📂 Import Target List (JSON/TXT)  [Ctrl+O]
├── 💾 Export Results (CSV/PDF)       [Ctrl+S]
├── 📝 Save System Logs
├── ─────────────────────────────────
└── ❌ Exit                           [Alt+F4]
```

### ⚙️ EDIT MENU
```
├── 📋 Copy Selected URL              [Ctrl+C]
├── 🧹 Clear Results (Reset view)
├── 🗑️ Remove Dead Links (Cleanup)
├── ─────────────────────────────────
└── 🔍 Find in Results               [Ctrl+F]
```

### 🔧 CONFIGURATION MENU
```
├── 🚀 Scan Parameters (Engine)
│   ├── Concurrency Settings
│   ├── Timeout Settings
│   └── Request Mode (HEAD/GET)
│
├── 🌐 Network & Anonymity
│   ├── Proxy Settings (HTTP/SOCKS)
│   ├── User-Agent Configuration
│   └── Request Throttling (Delay)
│
└── 🎨 Appearance
    ├── Theme: Light
    ├── Theme: Dark
    ├── Theme: Ghost
    ├── ─────────────────
    └── UI Scaling
```

### 🛠️ TOOLS MENU
```
├── ⚡ Service Database Generator
├── 📊 Session Statistics
├── 🔗 Proxy Checker
├── ─────────────────────────────────
└── 📧 Email Breach Checker (HIBP)
```

### ❓ HELP MENU
```
├── 📘 Documentation (GitHub Wiki)
├── 🐞 Report Bug (GitHub Issues)
├── ─────────────────────────────────
└── ℹ️ About / Author Info
```

## 🔍 Search Type Selector

The application now supports multiple search types:

```
Search Type: [Dropdown]
  ├── username
  ├── first_name
  ├── last_name
  └── email
```

Each search type updates the placeholder text dynamically:
- **username**: "Enter username to scan"
- **first_name**: "Enter first name to search"
- **last_name**: "Enter last name to search"
- **email**: "Enter email address to check"

## 🌐 Service Database

The application includes **98 pre-configured services** across categories:

### Major Categories:
- **Social Media** (9): Facebook, Instagram, Twitter, LinkedIn, TikTok, Snapchat, Reddit, Pinterest, Tumblr
- **Developer Platforms** (8): GitHub, GitLab, Bitbucket, StackOverflow, CodePen, Replit, HackerRank, LeetCode
- **Gaming** (7): Twitch, Steam, Xbox, PlayStation, Discord, Roblox, Epic
- **Music/Audio** (5): Spotify, SoundCloud, Bandcamp, Mixcloud, Last.fm
- **Video** (3): YouTube, Vimeo, Dailymotion
- **Messaging** (4): Telegram, Signal, WhatsApp, Skype
- **Photo/Art** (4): Flickr, 500px, DeviantArt, ArtStation
- **Professional** (6): Behance, Dribbble, Medium, Dev.to, ProductHunt, AngelList
- **And 52 more services!**

## 📧 Email Breach Checker

A dedicated dialog for checking email addresses against data breach databases (HIBP-style):

- Input field for email address
- Results display area
- Ready for API integration
- Clean, modern interface

## ⌨️ Keyboard Shortcuts

- **Ctrl+O**: Import Target List
- **Ctrl+S**: Export Results
- **Ctrl+C**: Copy Selected URL
- **Ctrl+F**: Find in Results
- **Alt+F4**: Exit Application

## 🎨 Features

All menu items are fully functional with:
- ✅ Configuration dialogs
- ✅ Settings persistence
- ✅ Error handling
- ✅ User feedback
- ✅ Modern UI design
