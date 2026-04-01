# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bachelor's thesis: a web-based math drill platform for basic school students with voice-based answer input. Students can answer math problems by speaking; audio is streamed over WebSocket to Azure Speech-to-Text, transcribed, then evaluated. Live at **superlectures.net** (VPS via `ssh vps-debian`).

## Commands

### Docker (recommended, runs full stack)
```bash
cd be
docker-compose build --no-cache
docker-compose up
# App at http://localhost:8000 — admin: admin1 / kockanenipes
docker-compose down --volumes --remove-orphans
```

### Backend (manual dev mode)
```bash
cd be
pip install -r requirements.txt
# Configure .env (see Environment section below)
python manage.py migrate
uvicorn be.asgi:application --host 0.0.0.0 --port 8000 --reload
```

### Frontend (dev mode, proxies to backend)
```bash
cd fe
npm install
npm run dev      # http://localhost:5173
npm run build    # production build
```

### Database seeding (after migrations)
```bash
cd be
python manage.py seed_grades
python manage.py setup_grade1_skills   # repeat for grades 1–9
python manage.py seed_grade1_drill_examples  # repeat for grades 1–9
```

## Environment Variables (`be/.env`)

```
DJANGO_SETTINGS_MODULE=be.settings
MYSQLDATABASE=drillovacka-demo
MYSQLUSER=root
MYSQLPASSWORD=secret
MYSQLHOST=localhost   # use 'db' inside Docker
MYSQLPORT=3307        # use 3306 inside Docker

AZURE_API_KEY=...
AZURE_REGION=francecentral
GEMINI_API_KEY=...

MEGA_UPLOAD_ENABLED=true
MEGA_EMAIL=...
MEGA_PASSWORD=...
MEGA_DELETE_LOCAL_AFTER_UPLOAD=false
```

## Architecture

### Stack
- **Backend**: Django 5.1 + Django REST Framework + Django Channels (ASGI), served by Uvicorn
- **Frontend**: Vue 3 (Composition API / `<script setup>`) + Vite + Pinia + Tailwind CSS
- **Database**: MySQL 8.0
- **Realtime**: Django Channels WebSockets (InMemoryChannelLayer — single-process only)
- **Reverse proxy**: Nginx (routes `/api/` and `/ws/` to Django, everything else to frontend SPA)

### Key Backend Files (`be/`)
| Path | Purpose |
|------|---------|
| `be/settings.py` | Django config (DB, CORS, Channels, WhiteNoise) |
| `be/asgi.py` | ASGI router — HTTP → Django, `/ws/*` → Channels consumers |
| `be/urls.py` | URL root; includes `api/urls.py` and serves built frontend |
| `api/models.py` | All data models |
| `api/views.py` | ~2600-line file with all REST API view functions |
| `api/urls.py` | All API URL patterns |
| `api/consumers.py` | WebSocket consumer for live speech + answer eval |
| `api/consumersSurvey.py` | WebSocket consumer for survey voice responses |
| `api/answerChecker.py` | Answer validation: inline, fraction, variable, Gemini AI |
| `api/attempt_cloud_sync.py` | Async MEGA cloud upload for attempt audio/JSON |

### Key Frontend Files (`fe/src/`)
| Path | Purpose |
|------|---------|
| `api/apiClient.js` | Axios instance + all HTTP API helpers; `getUserIdentifier()` returns `{student_id, session_id}` |
| `api/websocket.js` | WebSocket connection helpers |
| `stores/useRecorderStore.js` | Core audio recording state, WebSocket lifecycle, answer evaluation flow |
| `stores/useAuthStore.js` | Auth state (student/admin), login/logout, inactivity timer |
| `stores/useLanguageStore.js` | Active language (cs/sk/en) |
| `utils/dictionary.js` | All UI strings, keyed by language |
| `router/index.js` | Route definitions with `meta.requiresAdmin` / `meta.requiresAuth` guards |

### Data Model Relationships
```
Task (set of problems) → Example (individual problem) → Answer (correct answers)
Task ↔ Skill (M2M), Task ↔ GradeLevel (M2M)
Skill (hierarchical: parent_skill FK, related_skills M2M self)

Student / AnonymousSession (one required on attempts)
  → StudentExample (practice session record)
    → ExampleAttempt (each individual answer attempt, with audio_file_path, transcription, is_correct)
```

### Dual Identity Pattern
Every user is either a registered `Student` (identified by `student_id`) or an `AnonymousSession` (identified by `session_id`). This pair is passed in all API requests and WebSocket metadata. The helper `get_user_identity(request)` in `views.py` extracts whichever is present. A DB constraint enforces exactly one is set on `StudentExample` and `ExampleAttempt`.

### Voice Answer Flow
1. Frontend captures audio via RecordRTC + AudioWorklet processor
2. Binary audio frames sent over `WS /ws/speech/` alongside JSON metadata (student/session id, example id, language, etc.)
3. `consumers.py` streams audio to Azure Speech SDK, receives transcription
4. Transcription passed to `answerChecker.py` → evaluates correctness (inline math, fractions, variables, or Gemini fallback)
5. Result + full attempt log written to DB; audio saved to `be/attempt_audio/`
6. Cloud sync triggered asynchronously (MEGA upload)

### Answer Checking (`api/answerChecker.py`)
Four checker classes are tried in sequence depending on answer type:
- `InlineAnswerChecker` — numeric/simple text
- `FractionAnswerChecker` — fraction format
- `VariableAnswerChecker` — algebraic expressions
- `GeminiAnswerChecker` — AI fallback via Google Gemini API

### Admin vs Student Routes
Route access is controlled by `meta.requiresAdmin` (checks Pinia `useAuthStore.isAdmin`) and `meta.requiresAuth` (checks logged-in student). Most content is publicly accessible for anonymous sessions.

### Dropbox/Cloud Sync (production)
`rclone` syncs audio and JSON files from `be/audioprompts/` and `be/survey/` to Dropbox every 10 minutes via cron. Script: `be/scripts/sync_to_dropbox.sh`, config: `be/scripts/dropbox-sync.env`.
