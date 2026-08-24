import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

/** Swagger UI is served by the backend at `/docs` (outside /api/v1). */
function apiDocsUrl(): string {
  try {
    return new URL("/docs", API_BASE_URL).toString();
  } catch {
    return "http://localhost:8000/docs";
  }
}

export default function HomePage() {
  return (
    <main className="flex min-h-svh flex-1 items-center justify-center bg-muted/40 px-6 py-12">
      <div className="w-full max-w-2xl space-y-8">
        {/* Brand */}
        <header className="space-y-3 text-center">
          <div className="flex items-center justify-center gap-3">
            <span
              aria-hidden="true"
              className="flex size-11 items-center justify-center rounded-2xl bg-primary text-primary-foreground"
            >
              <svg
                viewBox="0 0 24 24"
                className="size-6"
                fill="none"
                stroke="currentColor"
                strokeWidth={2.5}
                strokeLinecap="round"
              >
                <path d="M12 5v14M5 12h14" />
              </svg>
            </span>
            <h1
              dir="ltr"
              className="font-heading text-3xl font-bold tracking-tight"
            >
              Clinical AI Copilot
            </h1>
          </div>
          <p className="text-muted-foreground">
            دستیار هوشمند بالینی برای پزشکان
          </p>
        </header>

        {/* Development status card */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <span className="relative flex size-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex size-2.5 rounded-full bg-emerald-500" />
              </span>
              <CardTitle>وضعیت محیط توسعه</CardTitle>
            </div>
            <CardDescription>بررسی راه‌اندازی اولیه پروژه</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <p className="text-lg leading-8 font-medium">
              محیط توسعه پروژه با موفقیت اجرا شده است.
            </p>

            <dl className="divide-y overflow-hidden rounded-lg border">
              <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
                <dt className="text-muted-foreground">
                  نشانی پایه سرویس (API)
                </dt>
                <dd dir="ltr" className="font-mono text-xs">
                  {API_BASE_URL}
                </dd>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
                <dt className="text-muted-foreground">وضعیت پایه پروژه</dt>
                <dd>
                  <Badge variant="secondary">آماده توسعه</Badge>
                </dd>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
                <dt className="text-muted-foreground">نسخه</dt>
                <dd dir="ltr" className="font-mono text-xs">
                  0.1.0
                </dd>
              </div>
            </dl>

            <Button
              render={
                <a href={apiDocsUrl()} target="_blank" rel="noreferrer" />
              }
            >
              مشاهده مستندات API
            </Button>
          </CardContent>
        </Card>

        <p className="text-center text-sm leading-7 text-muted-foreground">
          این سامانه فقط ابزار کمک به تصمیم‌گیری است و جایگزین پزشک نیست؛
          تصمیم نهایی همیشه با پزشک است.
        </p>
      </div>
    </main>
  );
}
