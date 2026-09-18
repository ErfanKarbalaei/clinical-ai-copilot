import Link from "next/link";
import {
  FileTextIcon,
  MicIcon,
  ShieldAlertIcon,
  SparklesIcon,
  UsersIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const CAPABILITIES = [
  {
    icon: UsersIcon,
    title: "پروندهٔ بالینی بیمار",
    description: "شرایط، آلرژی‌ها، داروها، آزمایش‌ها و یادداشت‌ها در یک نگاه",
  },
  {
    icon: FileTextIcon,
    title: "اسناد و استخراج متن",
    description: "آپلود اسناد، استخراج متن و تحلیل هوشمند با ذکر منبع",
  },
  {
    icon: MicIcon,
    title: "مستندسازی صوتی فارسی",
    description: "ضبط گفتار پزشک، تبدیل به متن و یادداشت بالینی پاک‌سازی‌شده",
  },
  {
    icon: ShieldAlertIcon,
    title: "بررسی ایمنی دارو",
    description: "تحلیل تداخل‌های دارویی بر اساس پروندهٔ واقعی بیمار",
  },
];

export default function HomePage() {
  return (
    <main className="flex min-h-svh flex-1 items-center justify-center px-6 py-12">
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
          <p className="text-lg text-muted-foreground">
            دستیار هوشمند بالینی برای پزشکان
          </p>
        </header>

        {/* Entry */}
        <div className="flex items-center justify-center gap-3">
          <Button size="lg" render={<Link href="/login" />}>ورود به سامانه</Button>
          <Button size="lg" variant="ghost" render={<Link href="/patients" />}>
            <UsersIcon />
            فهرست بیماران
          </Button>
        </div>

        {/* Capabilities */}
        <div className="grid gap-4 sm:grid-cols-2">
          {CAPABILITIES.map((capability) => (
            <Card key={capability.title} className="border-border/70">
              <CardHeader className="gap-2 pb-3">
                <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                  <capability.icon className="size-4 text-muted-foreground" />
                  {capability.title}
                </CardTitle>
                <CardDescription className="text-xs leading-5">
                  {capability.description}
                </CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>

        {/* Clinical responsibility note */}
        <Card className="ai-content">
          <CardContent className="flex items-start gap-3 py-4">
            <SparklesIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <p className="text-xs leading-6 text-muted-foreground">
              این سامانه صرفاً ابزار کمک به تصمیم‌گیری پزشک است؛ پاسخ‌های
              هوش مصنوعی بر اساس اطلاعات ثبت‌شدهٔ پروندهٔ بیمار تولید می‌شوند و
              جایگزین معاینه، قضاوت و تصمیم نهایی پزشک نیستند.
            </p>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
