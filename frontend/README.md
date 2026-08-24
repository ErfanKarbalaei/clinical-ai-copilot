# Frontend — Clinical AI Copilot

Next.js (App Router) + TypeScript + TailwindCSS + shadcn/ui.

The entire user interface is **Persian and right-to-left (RTL)**:

- `<html lang="fa" dir="rtl">` in `src/app/layout.tsx`
- `DirectionProvider` (Base UI) with `direction="rtl"`
- bundled **Vazirmatn** font (via the `vazirmatn` npm package — no external font CDN)
- shadcn/ui initialized with RTL support (`components.json` → `"rtl": true`)

Currently contains only the project foundation: the Persian RTL development
landing page. No clinical functionality yet.

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

Open http://localhost:3000

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
├── public/             # static assets
├── src/
│   ├── app/            # App Router pages/layouts (RTL, Persian)
│   ├── components/
│   │   └── ui/         # shadcn/ui components (button, card, badge, direction, ...)
│   └── lib/
│       └── utils.ts    # cn() helper
├── .env.example
├── next.config.ts
├── package.json
└── tsconfig.json
```
