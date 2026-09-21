import Link from "next/link";
import { StethoscopeIcon } from "lucide-react";

/** Landing navigation — same brand language as the app shell (Phase 4 Pen). */
export function LandingNav() {
  return (
    <header className="sticky top-0 z-40 border-b bg-card">
      <div className="mx-auto flex h-17 w-full max-w-[1440px] items-center justify-between gap-4 px-6 lg:px-16">
        {/* brand — right in RTL */}
        <Link href="/" className="flex shrink-0 items-center gap-2.5">
          <span className="flex size-7.5 items-center justify-center rounded-lg bg-brand text-primary-foreground">
            <StethoscopeIcon className="size-4" />
          </span>
          <span dir="ltr" className="text-base font-bold tracking-tight">
            Clinical AI Copilot
          </span>
        </Link>

        {/* anchor links — center */}
        <nav className="hidden items-center gap-7 lg:flex" aria-label="بخش‌های صفحه">
          <a href="#features" className="text-sm text-muted-foreground transition-colors hover:text-foreground">
            امکانات
          </a>
          <a href="#how-it-works" className="text-sm text-muted-foreground transition-colors hover:text-foreground">
            چطور کار می‌کند
          </a>
          <a href="#trust" className="text-sm text-muted-foreground transition-colors hover:text-foreground">
            اعتماد و ایمنی
          </a>
        </nav>

        {/* actions — left in RTL */}
        <div className="flex items-center gap-4">
          <Link
            href="/login"
            className="hidden text-sm font-medium text-muted-foreground transition-colors hover:text-foreground sm:inline"
          >
            ورود
          </Link>
          <Link
            href="/login"
            className="inline-flex h-9.5 items-center rounded-lg bg-brand px-4.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-brand-strong"
          >
            شروع استفاده
          </Link>
        </div>
      </div>
    </header>
  );
}
