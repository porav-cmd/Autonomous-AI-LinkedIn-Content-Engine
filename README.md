# 🚀 DevFlow: Autonomous AI LinkedIn Content Engine

An autonomous, multi-agent AI pipeline built with **LangGraph**, **LangChain**, **Groq LLM**, **Django ORM**, and the **Telegram Bot API**. It automatically generates high-value developer LinkedIn posts by alternating 50/50 between analyzing open-source GitHub repositories and curating trending technology news.

---

## ✨ Features

- **🤖 Multi-Agent LangGraph Orchestration:**
  - **Dynamic Decision Node:** Alternates 50/50 between GitHub project analysis and HackerNews developer trends.
  - **GitHub Code Analysis Node:** Scans repository trees, selects meaningful source files, and writes grounded first-person technical posts.
  - **HackerNews Analysis Node:** Parses top tech stories, extracts developer-focused angles, and writes neutral or first-person commentary.

- **💬 Human-in-the-Loop Telegram Bot:**
  - Interactive polling via Telegram: asks *"Do you want an AI-generated image for this post? (yes/no)"*.
  - Halts graph execution until the user replies directly in Telegram.

- **📊 100% Crisp Programmatic Infographic Cheat Sheet Generator:**
  - Built-in Pillow (`PIL`) rendering engine.
  - Generates 100% sharp, high-resolution visual cheat sheets with VS Code syntax-highlighted code blocks, sticky-note metrics ($O(1)$ complexity), and step-by-step workflow stages.
  - **Zero blurry AI squiggles or unsupported emoji boxes.**

- **🛡️ Deduplication & Persistence:**
  - Computes SHA-256 hashes of generated text to prevent duplicate topics or reposts.
  - Permanently stores all posts, topics, and image paths in a Django SQLite / PostgreSQL database.

- **☁️ Cloud Automated Execution (Render / GitHub Actions):**
  - Includes `render.yaml` and `dj-database-url` for daily automated cloud execution without needing a local machine running.

---

## 🏗️ Architecture Flow

```text
                               +-----------------------------+
                               |    START (LangGraph Entry)  |
                               +-----------------------------+
                                              |
                                     [select_post_type]
                                    /                  \
                      (If "Project")                    (If "News")
                            v                                v
            +------------------------------+  +-----------------------------+
            | github_topic_node            |  | fetch_news_node             |
            | (Repo Analysis & File Tree)  |  | (HackerNews API Fetching)   |
            +------------------------------+  +-----------------------------+
                            |                                |
            +------------------------------+  +-----------------------------+
            | generate_topic_node          |  | generate_news_topic_node    |
            +------------------------------+  +-----------------------------+
                            |                                |
            +------------------------------+  +-----------------------------+
            | draft_node (LLM Generation)  |  | news_draft_node (LLM Draft) |
            +------------------------------+  +-----------------------------+
                            \                                /
                             +--------------+---------------+
                                            |
                                            v
                             +------------------------------+
                             | dedup_node (SHA-256 Check)   |
                             +------------------------------+
                                            |
                                            v
                             +------------------------------+
                             | ask_image_node               |
                             | (Telegram Question & Wait)   |
                             +------------------------------+
                                            |
                                    [route_on_image]
                                   /                \
                         (If "yes")                  (If "no")
                             v                           v
              +----------------------------+   +-------------------+
              | image_node (Pillow Sheet)  |   | send_final_node   |
              +----------------------------+   | (Telegram Upload) |
                             \                           ^
                              +--------------------------+
                                                         |
                                                         v
                                              +---------------------+
                                              | save_node (Django)  |
                                              +---------------------+
                                                         |
                                                         v
                                                        END
```

---

## 🛠️ Project Structure

```text
├── myapp/
│   ├── service/
│   │   └── agent.py          # Core LangGraph pipeline & PIL cheat sheet generator
│   ├── models.py             # Django Post model for DB persistence
│   └── views.py              # Django views
├── project/
│   ├── settings.py           # Django configuration (SQLite / PostgreSQL)
│   └── urls.py               # Main URL routing
├── github.py                 # GitHub API fetching, rate-limit fallbacks & README parser
├── news.py                   # HackerNews API scraper & content parser
├── telegram.py               # Telegram Bot API (sendMessage, sendPhoto, wait_for_reply)
├── requirements.txt          # Python dependencies
├── render.yaml               # Render Cloud Cron Job deployment blueprint
├── manage.py                 # Django CLI management script
└── .env.example              # Sample environment configuration
```

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
- Python 3.10+
- Telegram Bot Token & Chat ID (from [@BotFather](https://t.me/BotFather))
- Groq API Key (from [Groq Console](https://console.groq.com))

### 2. Installation
Clone the repository and install dependencies:

```bash
git clone https://github.com/porav-cmd/DevFlow.git
cd DevFlow

# Create & activate virtual environment
python -m venv .venv
.venv\Scripts\activate   # On Windows
source .venv/bin/activate # On Linux/macOS

# Install required packages
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory:

```env
TELEGRAM_BOT_TOKEN=1234567890:AAEgB3UD...
TELEGRAM_CHAT_ID=1875595995
GROQ_API_KEY=gsk_your_groq_api_key_here
GITHUB_TOKEN=ghp_optional_github_token_here
```

### 4. Database Setup
Run Django migrations to create database tables:

```bash
python manage.py migrate
```

### 5. Execution
Run the automated pipeline:

```bash
python -m myapp.service.agent
```

---

## ☁️ Cloud Deployment (Render Cron Job)

To run this pipeline daily in the cloud without keeping your computer on:

1. **Push your code to GitHub.**
2. **Create a Free PostgreSQL Database on Render.com.**
3. **Create a Cron Job on Render:**
   - **Schedule:** `0 9 * * *` (Daily at 9:00 AM UTC)
   - **Build Command:** `pip install -r requirements.txt && python manage.py migrate`
   - **Command:** `python -m myapp.service.agent`
4. **Set Environment Variables on Render:**
   - `DATABASE_URL` (From Render PostgreSQL)
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `GROQ_API_KEY`

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
