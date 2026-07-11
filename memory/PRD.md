# PawCare — PRD

## Original Problem Statement
Webapp semplice per proprietari di animali domestici per tracciare visite veterinarie, vaccini, trattamenti antiparassitari, con notifiche personalizzate e consigli su cura/prevenzione basati su età e razza, con l'aiuto dell'AI. (Italian UI)

## Architecture
- Frontend: React (CRA + craco), TailwindCSS, Shadcn UI, framer-motion, @phosphor-icons/react
- Backend: FastAPI (routes under /api), MongoDB (motor)
- AI: Claude Sonnet 4.6 via emergentintegrations (Emergent LLM key)
- Auth: Email+Password (JWT access_token cookie) + Emergent Google OAuth (session_token cookie)

## User Personas
- Pet owner tracking health records of one or more dogs/cats.

## Core Requirements (static)
- Pet profiles (name, species dog/cat, breed, birth date, sex, weight, photo)
- Vet visits, vaccines, antiparasitic treatments logs
- In-app dashboard "Prossime scadenze" (upcoming due dates)
- AI care advice by age/breed + AI chat assistant
- Care guides filtered by species/age

## Implemented (2026-07-11)
- Auth (email/password + Google), seeded admin (admin@pawcare.it / admin123)
- Pets CRUD with photo (base64), age auto-calc
- Visits/Vaccines/Treatments CRUD per pet
- Dashboard with pet grid + upcoming due dates
- AI advice + AI chat with conversation memory + STREAMING token-by-token (SSE /ai/chat/stream)
- Guides library with species/age filter
- Weight tracking + trend chart (recharts)
- PWA installable (manifest + service worker + icons)
- Web Push notifications: VAPID, subscribe/unsubscribe, reminders (due within 7 days, deduped)
- Background scheduler (APScheduler) daily 08:00 UTC + admin /push/run-batch
- Medical document attachments per pet (Emergent Object Storage: upload/list/download/soft-delete, 15MB cap, owner isolation)
- Multi-pet calendar view (/calendario)
- Admin dashboard (/admin, admin-only): stats + elenco utenti registrati con provider, data registrazione, n. animali/chat/push
- PWA install banner guidato (Android beforeinstallprompt + istruzioni iOS), dismissibile
- Tested: 82/82 backend, 100% frontend across 8 iterations

## Backlog / Next
- P0: Abbonamento/monetizzazione (Stripe) — in definizione con l'utente
- P1: Email reminders alternative (Resend/SendGrid)
- P2: Configurable reminder lead-time & send hour per user
