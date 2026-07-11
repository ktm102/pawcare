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
- Dashboard with pet grid + upcoming due dates (sorted by days_left)
- AI advice endpoint + AI chat with persistent history + CONVERSATION MEMORY (initial_messages)
- Guides library (8 seeded guides) with species/age filter
- Weight tracking + trend chart (recharts) per pet
- PWA: installable (manifest.json + service worker), app icons
- Web Push notifications: VAPID keys, subscribe/unsubscribe, reminders for items due within 7 days (deduped), in-app toggle in header
- Full design system (Organic & Earthy theme, Manrope/Outfit fonts)
- Tested: 47/47 backend, 100% frontend flows across 4 iterations

## Backlog / Next
- P1: Email reminders as alternative to web push (Resend/SendGrid)
- P1: Streaming AI chat responses (SSE) for token-by-token UX
- P1: Background scheduler (APScheduler) to send push reminders even when app is closed (currently triggered on dashboard load)
- P2: Medical document attachments, multi-pet calendar view, object storage for photos
