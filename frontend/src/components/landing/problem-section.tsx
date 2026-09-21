"use client";

import { ArrowDownIcon, FilesIcon, LayersIcon, PillIcon, SparklesIcon, TimerIcon } from "lucide-react";

import { Reveal } from "./reveal";

const PROBLEMS = [
  {
    icon: FilesIcon,
    title: "پرونده‌های طولانی",
    description: "سال‌ها سابقهٔ بالینی که باید در چند دقیقه مرور شود.",
  },
  {
    icon: LayersIcon,
    title: "اطلاعات پراکنده",
    description: "آزمایش، دارو و سند در جای‌های جدا و بدون ارتباط.",
  },
  {
    icon: PillIcon,
    title: "پیچیدگی دارویی",
    description: "تداخل‌ها و آلرژی‌ها باید پیش از هر نسخه بررسی شوند.",
  },
  {
    icon: TimerIcon,
    title: "زمان محدود پزشک",
    description: "دقایق طلایی ویزیت، جای جست‌وجوی دستی نیست.",
  },
];

const MESSY_BARS = [
  "left-[10%] top-[16%] w-[30%] rotate-[8deg]",
  "left-[50%] top-[19%] w-[25%] -rotate-[6deg]",
  "left-[25%] top-[33%] w-[37%] rotate-[3deg]",
  "left-[15%] top-[49%] w-[27%] -rotate-[9deg]",
  "left-[47%] top-[55%] w-[32%] rotate-[5deg]",
  "left-[28%] top-[69%] w-[22%] -rotate-[4deg]",
  "left-[57%] top-[10%] w-[18%] rotate-[12deg]",
];

/** Phase 4 problem section — clinical challenges + before/after visualization. */
export function ProblemSection() {
  return (
    <section className="bg-card">
      <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-12 px-6 py-22 lg:px-0">
        <Reveal className="flex flex-col items-center gap-3 text-center">
          <p className="text-[13px] font-semibold text-brand">چالش</p>
          <h2 className="text-[26px] font-bold sm:text-[32px]">
            پرونده‌های شلوغ، زمانِ اندکِ پزشک
          </h2>
          <p className="max-w-[520px] text-[15px] leading-8 text-muted-foreground">
            اطلاعات حیاتی بیمار پراکنده است و مرور آن زمانی می‌برد که پزشک
            ندارد.
          </p>
        </Reveal>

        <div className="flex flex-col gap-12 lg:flex-row lg:items-start lg:gap-14">
          {/* problems — right in RTL */}
          <Reveal className="flex w-full flex-col gap-5 lg:w-1/2">
            {PROBLEMS.map((problem) => (
              <div key={problem.title} className="flex items-start gap-3.5">
                <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-brand-soft text-brand">
                  <problem.icon className="size-5" />
                </span>
                <div className="space-y-1">
                  <h3 className="text-base font-semibold">{problem.title}</h3>
                  <p className="text-[13px] leading-6 text-muted-foreground">
                    {problem.description}
                  </p>
                </div>
              </div>
            ))}
          </Reveal>

          {/* before/after — left in RTL */}
          <Reveal delay={0.15} className="w-full lg:w-1/2">
            <div className="flex flex-col gap-4">
              {/* before */}
              <div className="relative h-[220px] rounded-2xl border bg-background p-4">
                <span className="absolute right-4 top-3.5 z-10 inline-flex h-6 items-center rounded-md bg-surface-2 px-2.5 text-[11px] text-muted-foreground">
                  امروز — اطلاعات پیچیدهٔ بیمار
                </span>
                {MESSY_BARS.map((bar, index) => (
                  <span key={index} className={`absolute h-3 rounded-full bg-border ${bar}`} />
                ))}
              </div>

              <div className="flex justify-center">
                <span className="flex size-9 items-center justify-center rounded-full bg-brand text-primary-foreground shadow-[0_8px_18px_#0F766E33]">
                  <ArrowDownIcon className="size-4" />
                </span>
              </div>

              {/* after */}
              <div className="space-y-2.5 rounded-2xl border border-brand-border bg-card p-4">
                <span className="inline-flex h-6 items-center rounded-md bg-brand-soft px-2.5 text-[11px] font-semibold text-brand">
                  با Clinical AI Copilot — بینشِ سازمان‌یافته
                </span>
                <div className="flex items-start gap-2.5">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-brand-soft text-brand">
                    <SparklesIcon className="size-4" />
                  </span>
                  <div className="space-y-1">
                    <p className="text-[13px] font-medium leading-6">
                      بیمار ۶۷ ساله با دیابت، فشار خون و بیماری کلیوی (مرحله ۳)
                    </p>
                    <p className="text-[11px] leading-5 text-muted-foreground">
                      هشدار: پتاسیم بحرانی — تداخل بالقوهٔ وارفارین · منبع: ۴
                      رکورد پرونده
                    </p>
                  </div>
                </div>
                {[
                  { label: "آلرژی شدید", value: "پنی‌سیلین", critical: true },
                  { label: "داروهای فعال", value: "۴ دارو", critical: false },
                  { label: "آزمایش بحرانی", value: "K 5.9", critical: true },
                ].map((row) => (
                  <div key={row.label} className="flex items-center justify-between px-0.5">
                    <span className="text-xs text-muted-foreground">{row.label}</span>
                    <span className={`text-xs font-semibold ${row.critical ? "text-critical" : ""}`}>
                      {row.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
