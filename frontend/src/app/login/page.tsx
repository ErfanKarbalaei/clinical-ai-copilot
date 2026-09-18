"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { LoaderIcon, LogInIcon, UserPlusIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { login, register } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isRegister = mode === "register";

  function switchMode(next: "login" | "register") {
    setMode(next);
    setError(null);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      if (isRegister) {
        // register creates a doctor account, then logs in immediately
        await register(email.trim(), password, fullName.trim());
      } else {
        await login(email.trim(), password);
      }
      router.push("/patients");
      router.refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "عملیات ناموفق بود.");
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 items-center px-4 py-16">
      <Card className="w-full">
        <CardHeader className="space-y-3 text-center">
          <div className="flex justify-center">
            <span
              aria-hidden="true"
              className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground"
            >
              <svg
                viewBox="0 0 24 24"
                className="size-5"
                fill="none"
                stroke="currentColor"
                strokeWidth={2.5}
                strokeLinecap="round"
              >
                <path d="M12 5v14M5 12h14" />
              </svg>
            </span>
          </div>
          <div className="space-y-1">
            <CardTitle className="text-lg">
              {isRegister ? "ثبت‌نام پزشک" : "ورود به سامانه"}
            </CardTitle>
            <CardDescription>
              {isRegister
                ? "ساخت حساب پزشک — پس از ثبت‌نام به‌طور خودکار وارد می‌شوید."
                : "دستیار هوشمند بالینی — برای دسترسی به پروندهٔ بیماران وارد شوید."}
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister ? (
              <div className="space-y-2">
                <Label htmlFor="fullName">نام و نام خانوادگی *</Label>
                <Input
                  id="fullName"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  required
                  maxLength={200}
                  autoComplete="name"
                  placeholder="مثال: دکتر سارا محمدی"
                />
              </div>
            ) : null}
            <div className="space-y-2">
              <Label htmlFor="email">ایمیل *</Label>
              <Input
                id="email"
                type="email"
                dir="ltr"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                autoComplete="email"
                placeholder="doctor@example.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">گذرواژه *</Label>
              <Input
                id="password"
                type="password"
                dir="ltr"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={8}
                autoComplete={isRegister ? "new-password" : "current-password"}
              />
              {isRegister ? (
                <p className="text-[11px] text-muted-foreground">
                  حداقل ۸ کاراکتر — نقش پیش‌فرض «پزشک» است.
                </p>
              ) : null}
            </div>
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? (
                <LoaderIcon className="animate-spin" />
              ) : isRegister ? (
                <UserPlusIcon />
              ) : (
                <LogInIcon />
              )}
              {submitting
                ? "در حال پردازش…"
                : isRegister
                  ? "ثبت‌نام و ورود"
                  : "ورود"}
            </Button>
          </form>

          <p className="mt-4 text-center text-sm text-muted-foreground">
            {isRegister ? "حساب کاربری دارید؟" : "حساب کاربری ندارید؟"}{" "}
            <Button
              type="button"
              variant="link"
              className="h-auto p-0"
              onClick={() => switchMode(isRegister ? "login" : "register")}
            >
              {isRegister ? "ورود" : "ثبت‌نام"}
            </Button>
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
