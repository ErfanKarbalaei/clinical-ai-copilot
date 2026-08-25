import Link from "next/link";
import { UsersIcon } from "lucide-react";

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

        {/* Entry point */}
        <Card>
          <CardHeader>
            <CardTitle>محیط توسعه پروژه با موفقیت اجرا شده است.</CardTitle>
            <CardDescription>
              بخش مدیریت بیماران آماده است؛ قابلیت‌های دیگر در مراحل بعدی اضافه می‌شوند.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <dl className="divide-y overflow-hidden rounded-lg border">
              <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
                <dt className="text-muted-foreground">نشانی پایه سرویس (API)</dt>
                <dd dir="ltr" className="font-mono text-xs">
                  {API_BASE_URL}
                </dd>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
                <dt className="text-muted-foreground">وضعیت پروژه</dt>
                <dd>
                  <Badge variant="secondary">مدیریت بیماران فعال است</Badge>
                </dd>
              </div>
            </dl>

            <Button size="lg" className="w-full" render={<Link href="/patients" />}>
              <UsersIcon />
              ورود به فهرست بیماران
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
