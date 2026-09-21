"use client";

import {
  BadgeCheckIcon,
  ClipboardListIcon,
  FlaskConicalIcon,
  PillIcon,
  SearchIcon,
  SparklesIcon,
  StethoscopeIcon,
  TriangleAlertIcon,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Reveal } from "./reveal";

const MINI_EVIDENCE: { type: string; desc: string; icon: LucideIcon }[] = [
  { type: "آزمایش", desc: "HbA1c — 8.2%", icon: FlaskConicalIcon },
  { type: "دارو", desc: "وارفارین — 5 mg", icon: PillIcon },
];

const EVIDENCE_ITEMS: { type: string; desc: string; icon: LucideIcon }[] = [
  { type: "داروی فعال", desc: "وارفارین — ۵ میلی‌گرم", icon: PillIcon },
  { type: "آزمایش", desc: "پتاسیم (K) — 5.9", icon: FlaskConicalIcon },
  { type: "یادداشت ویزیت", desc: "پیگیری دیابت — ۲۵ شهریور", icon: ClipboardListIcon },
];

/**
 * Phase 4 product preview — a browser-framed miniature of the REAL product
 * (patient workspace + copilot + evidence), built with the same UI language.
 */

function MiniRow({ title, meta, metaClass }: { title: string; meta: string; metaClass?: string }) {
  return (
    <div className="flex w-full items-center justify-between">
      <span className="truncate text-[8px] font-medium">{title}</span>
      <span className={`shrink-0 text-[7px] ${metaClass ?? "text-muted-foreground"}`}>{meta}</span>
    </div>
  );
}

function BrowserMockup() {
  return (
    <div className="flex h-full w-full flex-col overflow-hidden rounded-2xl border bg-card text-foreground shadow-[0_24px_60px_#1C2B2A1F]">
      {/* chrome */}
      <div className="relative flex h-9.5 shrink-0 items-center justify-center border-b bg-background">
        <span className="flex gap-1.5 absolute start-3.5">
          <span className="size-2 rounded-full bg-[#E8B4B0]" />
          <span className="size-2 rounded-full bg-[#F2D9A9]" />
          <span className="size-2 rounded-full bg-[#BFE3C8]" />
        </span>
        <span
          dir="ltr"
          className="inline-flex h-5.5 items-center rounded-full border bg-card px-3 font-mono text-[10px] text-muted-foreground"
        >
          app.clinical-ai.copilot/patients/50
        </span>
      </div>

      {/* app shell strip */}
      <div className="flex h-7.5 shrink-0 items-center justify-between border-b bg-card px-3.5">
        <span className="flex items-center gap-1.5">
          <span className="flex size-4 items-center justify-center rounded bg-brand">
            <StethoscopeIcon className="size-2.5 text-primary-foreground" />
          </span>
          <span dir="ltr" className="text-[9px] font-bold">
            Clinical AI Copilot
          </span>
        </span>
        <span className="hidden h-4.5 w-50 items-center rounded-full bg-surface-2 px-2 text-[8px] text-muted-foreground sm:flex">
          جست‌وجوی بیمار…
        </span>
        <span className="flex size-4.5 items-center justify-center rounded-full bg-brand-soft text-[8px] font-bold text-brand">
          س
        </span>
      </div>

      {/* identity strip */}
      <div className="flex h-9 shrink-0 items-center justify-between border-b bg-card px-3.5">
        <span className="flex items-center gap-1.5">
          <span className="flex size-5 items-center justify-center rounded-full bg-brand-soft text-[7px] font-bold text-brand">
            ز.م
          </span>
          <span className="flex flex-col">
            <span className="text-[10px] leading-4 font-bold">زهرا محمدی</span>
            <span className="text-[7px] leading-3 text-muted-foreground">
              ۶۸ ساله · زن · 0065432101
            </span>
          </span>
        </span>
        <span className="flex h-4 items-center gap-1 rounded border border-critical-border bg-critical-soft px-1.5 text-[7px] font-semibold text-critical">
          <TriangleAlertIcon className="size-2" />
          آلرژی شدید: پنی‌سیلین
        </span>
      </div>

      {/* tabs strip */}
      <div className="flex h-6 shrink-0 items-end gap-3.5 border-b bg-card px-3.5">
        {["اسناد و یادداشت‌ها", "آزمایش‌ها", "داروها", "تایم‌لاین"].map((tab) => (
          <span key={tab} className="pb-1 text-[8px] text-muted-foreground">
            {tab}
          </span>
        ))}
        <span className="relative pb-1 text-[8px] font-semibold text-brand">
          خلاصه
          <span className="absolute inset-x-0 -bottom-px mx-auto h-[1.5px] w-3 rounded-full bg-brand" />
        </span>
      </div>

      {/* body */}
      <div className="flex min-h-0 flex-1">
        {/* record column */}
        <div className="flex min-w-0 flex-1 flex-col gap-1.5 p-2.5">
          <div className="flex h-6.5 shrink-0 items-center justify-between rounded-lg border border-critical-border bg-critical-soft px-2">
            <span className="text-[8px] font-semibold text-critical">
              حساسیت شدید — پنی‌سیلین
            </span>
            <TriangleAlertIcon className="size-2.5 text-critical" />
          </div>
          <div className="flex flex-col gap-1 rounded-lg border bg-card p-2">
            <span className="text-[8px] font-semibold">مشکلات فعال — ۲</span>
            <MiniRow title="دیابت نوع ۲" meta="از ۱۳۹۸" />
            <MiniRow title="فشار خون بالا" meta="از ۱۴۰۱" />
          </div>
          <div className="grid flex-1 grid-cols-2 gap-1.5">
            <div className="flex flex-col gap-1 rounded-lg border bg-card p-2">
              <span className="text-[8px] font-semibold">حساسیت‌ها — ۲</span>
              <MiniRow title="پنی‌سیلین" meta="شدید" metaClass="text-[7px] text-critical" />
              <MiniRow title="آسپرین" meta="متوسط" metaClass="text-[7px] text-warning" />
            </div>
            <div className="flex flex-col gap-1 rounded-lg border bg-card p-2">
              <span className="text-[8px] font-semibold">داروهای فعال — ۲</span>
              <MiniRow title="وارفارین" meta="5 mg" metaClass="font-mono text-[7px]" />
              <MiniRow title="متفورمین" meta="500 mg" metaClass="font-mono text-[7px]" />
            </div>
          </div>
        </div>

        {/* copilot column */}
        <div className="flex w-[300px] shrink-0 flex-col gap-1.5 border-s bg-surface-2 p-2">
          <div className="flex shrink-0 items-center justify-end gap-1.5">
            <span className="flex flex-col items-end">
              <span className="text-[9px] leading-4 font-bold">دستیار بالینی</span>
              <span className="text-[6px] leading-3 text-muted-foreground">
                پاسخ‌ها بر اساس پروندهٔ بیمار
              </span>
            </span>
            <SparklesIcon className="size-2.5 text-brand" />
          </div>
          <div className="shrink-0 rounded-lg border bg-card px-1.5 py-1 text-[8px] font-medium">
            خلاصهٔ وضعیت بالینی بیمار چیست؟
          </div>
          <div className="flex flex-col gap-1 rounded-lg border border-brand-border bg-brand-soft p-2">
            <span className="border-s-2 border-brand ps-1.5 text-[7px] font-semibold text-brand">
              خلاصه
            </span>
            <p className="text-[8px] leading-[1.7]">
              بیمار ۶۸ ساله با دیابت نوع ۲، فشار خون بالا و بیماری کلیوی مزمن
              (مرحله ۳).
            </p>
            <div className="flex flex-col gap-1 border-t border-brand-border pt-1">
              <span className="text-[6px] font-semibold text-muted-foreground">
                منابع استفاده‌شده — ۳
              </span>
              {MINI_EVIDENCE.map((item) => (
                <span
                  key={item.desc}
                  className="flex items-center gap-1.5 rounded bg-card px-1.5 py-0.5"
                >
                  <item.icon className="size-2 text-muted-foreground" />
                  <span className="flex-1 truncate text-[7px] font-medium">{item.desc}</span>
                  <span className="text-[6px] text-muted-foreground">{item.type}</span>
                </span>
              ))}
            </div>
          </div>
          <div className="mt-auto flex h-6 shrink-0 items-center rounded-lg border bg-card px-1.5 text-[7px] text-muted-foreground">
            سؤال خود را بنویسید…
          </div>
        </div>
      </div>
    </div>
  );
}

/** Floating evidence card that overlaps the mockup (desktop). */
function EvidenceCard() {
  return (
    <div className="absolute -bottom-10 end-0 hidden w-[300px] flex-col gap-2.5 rounded-2xl border bg-card p-4 shadow-[0_20px_44px_#1C2B2A26] lg:flex">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold">منابع استفاده‌شده</span>
        <span className="inline-flex h-4.5 items-center rounded bg-brand-soft px-1.5 text-[9px] text-brand">
          ۳ منبع
        </span>
      </div>
      {EVIDENCE_ITEMS.map((item) => (
        <div
          key={item.desc}
          className="flex items-center gap-2 rounded-lg bg-background px-2 py-1.5"
        >
          <span className="flex-1 truncate text-[11px] font-medium">{item.desc}</span>
          <span className="text-[9px] text-muted-foreground">{item.type}</span>
          <span className="flex size-5 items-center justify-center rounded-md bg-surface-2">
            <item.icon className="size-2.5 text-muted-foreground" />
          </span>
        </div>
      ))}
      <div className="flex justify-end">
        <span className="text-[10px] font-medium text-brand">
          هر پاسخ، به رکورد واقعی پرونده گره خورده است ›
        </span>
      </div>
      <span className="absolute -top-3 start-4 flex items-center gap-1 rounded-full border bg-card px-2 py-0.5 text-[10px] font-medium text-brand shadow-sm">
        <BadgeCheckIcon className="size-3" />
        شفافیت منابع
      </span>
    </div>
  );
}

export function ProductPreview() {
  return (
    <section className="bg-card pb-20">
      <div className="mx-auto flex w-full max-w-[1240px] flex-col items-center gap-12 px-6">
        <Reveal className="flex flex-col items-center gap-3 text-center">
          <p className="text-[13px] font-semibold text-brand">محصول</p>
          <h2 className="text-[26px] font-bold sm:text-[32px]">محیط کار واقعی پزشک</h2>
          <p className="text-[15px] text-muted-foreground">
            پروندهٔ بیمار و دستیار هوشمند، کنار هم در یک فضای کاری
          </p>
        </Reveal>
        <Reveal delay={0.15} className="relative w-full">
          <div className="h-[520px] sm:h-[560px]">
            <BrowserMockup />
          </div>
          <EvidenceCard />
          <span className="absolute -top-3 start-6 hidden items-center gap-1.5 rounded-full border bg-card px-2.5 py-1 text-[11px] font-medium text-muted-foreground shadow-sm md:flex">
            <SearchIcon className="size-3 text-brand" />
            فضای کاری بیمار در محصول واقعی
          </span>
        </Reveal>
      </div>
    </section>
  );
}
