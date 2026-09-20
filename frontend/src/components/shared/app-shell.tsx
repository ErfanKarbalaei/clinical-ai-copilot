import Link from "next/link";
import { SearchIcon, StethoscopeIcon } from "lucide-react";

import { LogoutButton } from "@/components/shared/logout-button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { AuthUser } from "@/lib/auth";

/**
 * Persistent top App Shell (Phase 1 design):
 * brand on the right, global patient search in the center, current
 * physician + logout on the left — Persian RTL throughout.
 */
export async function AppShell() {
  let user: AuthUser | null = null;
  try {
    user = await api.getMe();
  } catch {
    user = null;
  }
  const initials =
    user?.full_name
      ?.trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part.charAt(0))
      .join(" ") ?? null;

  return (
    <header className="sticky top-0 z-40 border-b bg-card">
      <div className="flex h-13 items-center justify-between gap-4 px-4 lg:px-6">
        {/* brand — right in RTL */}
        <Link href="/patients" className="flex shrink-0 items-center gap-2.5">
          <span className="flex size-7 items-center justify-center rounded-lg bg-brand text-primary-foreground">
            <StethoscopeIcon className="size-4" />
          </span>
          <span dir="ltr" className="text-[15px] font-bold tracking-tight">
            Clinical AI Copilot
          </span>
        </Link>

        {/* جست‌وجوی سراسری بیمار — وسط نوار */}
        <form action="/patients" className="hidden w-full max-w-md md:block">
          <div className="relative">
            <SearchIcon className="absolute start-3 top-1/2 size-4 -translate-y-1/2 text-faint" />
            <Input
              name="q"
              placeholder="جست‌وجوی بیمار، کد ملی یا شماره پرونده…"
              className="h-8.5 border-transparent bg-surface-2 ps-9 text-xs"
            />
          </div>
        </form>

        {/* current physician — left in RTL */}
        <div className="flex shrink-0 items-center gap-2">
          <LogoutButton />
          {user ? (
            <span className="flex items-center gap-2" title={user.email}>
              <span className="hidden text-xs font-medium sm:inline">
                {user.full_name}
              </span>
              <span className="flex size-7.5 items-center justify-center rounded-full bg-brand-soft text-[11px] font-semibold text-brand">
                {initials}
              </span>
            </span>
          ) : null}
        </div>
      </div>
    </header>
  );
}
