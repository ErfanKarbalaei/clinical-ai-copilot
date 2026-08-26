# Frontend — Clinical AI Copilot

Next.js (App Router) + TypeScript + TailwindCSS + shadcn/ui.

The entire user interface is **Persian and right-to-left (RTL)**:

- `<html lang="fa" dir="rtl">` in `src/app/layout.tsx`
- `DirectionProvider` (Base UI) with `direction="rtl"`
- bundled **Vazirmatn** font (via the `vazirmatn` npm package — no external font CDN)
- shadcn/ui initialized with RTL support (`components.json` → `"rtl": true`)
- Persian (Jalali) date formatting via `Intl` + `fa-IR`

## Pages

| Route | Description |
| --- | --- |
| `/` | Landing page — status + entry point to the patients list |
| `/patients` | Patient list (server-rendered): search by name/national code, pagination, «بیمار جدید» dialog |
| `/patients/[id]` | Patient clinical record (server-rendered from `/overview` + `/documents`): profile, conditions, allergies, active medications (add/edit/**stop**/delete), documents (upload/status/download/extracted text/delete), 5 recent labs, 5 recent notes |

All data comes from the backend REST API (`src/lib/api.ts`) — there is no
hardcoded/mock patient data in the frontend.

## Setup

```bash
cd frontend
npm install
cp .env.example .env.local   # adjust NEXT_PUBLIC_API_URL if needed
```

## Run (development)

```bash
npm run dev
```

Open http://localhost:3000 — the backend (and PostgreSQL) must be running
for the patients pages to show data.

## Production build

```bash
npm run build
npm run start
```

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Public base URL of the backend API (inlined at build time — rebuild after changing) | `http://localhost:8000/api/v1` |

## Structure

```
frontend/
├── public/                 # static assets
├── src/
│   ├── app/
│   │   ├── page.tsx        # landing page
│   │   ├── not-found.tsx   # Persian 404
│   │   └── patients/
│   │       ├── page.tsx            # patient list (server component)
│   │       └── [id]/page.tsx       # patient record (server component)
│   ├── components/
│   │   ├── patients/       # clinical UI (forms, row actions, dialogs)
│   │   ├── shared/         # empty/error states, confirm dialog
│   │   └── ui/             # shadcn/ui components (RTL-aware)
│   └── lib/
│       ├── api.ts          # typed API client (fetch, no external deps)
│       ├── types.ts        # API response/payload types
│       ├── format.ts       # Persian labels + Jalali date/age helpers
│       └── utils.ts        # cn() helper
├── .env.example
├── next.config.ts
├── package.json
└── tsconfig.json
```

## Notes

- Pages are dynamic (`force-dynamic`) and fetch with `cache: "no-store"` —
  patient data is always fresh; mutations call the API then
  `router.refresh()`.
- Clinical sections are read-only server components with small client
  components for the interactive parts (dialogs, delete confirmations).
- Not implemented yet (later phases): documents, voice notes, AI
  summaries, timeline view, evidence/citations.
