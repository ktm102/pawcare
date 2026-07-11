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
- AI advice endpoint + AI chat with persistent history
- Guides library (8 seeded guides) with species/age filter
- Full design system (Organic & Earthy theme, Manrope/Outfit fonts)
- Tested: 26/26 backend, 100% frontend flows

## Backlog / Next
- P1: Real email/push notifications for due dates (SendGrid) — currently in-app only
- P1: Streaming AI chat responses (SSE) for token-by-token UX
- P2: Weight tracking over time (chart), medical document attachments
- P2: Multi-pet reminders calendar view
- P2: Object storage for photos instead of base64
