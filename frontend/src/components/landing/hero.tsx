"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import {
  BadgeCheckIcon,
  BrainIcon,
  FlaskConicalIcon,
  HistoryIcon,
  FileTextIcon,
  PillIcon,
  PlayIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Clinical Intelligence Core — faithful vector reproduction of the Pen Phase
 * 4 hero visual (single SVG, Pen radii around center 300,300: rings 260/200/
 * 140, glow 110, core 95/80) with the six floating record chips positioned
 * at the Pen coordinates. No image assets, no 3D.
 */

const CHIPS: {
  label: string;
  icon: LucideIcon;
  left: string;
  top: string;
  emphasized?: boolean;
  visibility: string;
  delay: number;
  duration: number;
}[] = [
  { label: "پروندهٔ بیمار", icon: FileTextIcon, left: "73.6%", top: "18.2%", visibility: "flex", delay: 0, duration: 6 },
  { label: "نتایج آزمایش", icon: FlaskConicalIcon, left: "13.1%", top: "36.2%", visibility: "flex", delay: 0.8, duration: 7 },
  { label: "اطلاعات دارویی", icon: PillIcon, left: "80.6%", top: "60.2%", visibility: "flex", delay: 1.6, duration: 6.5 },
  { label: "شواهد و منابع", icon: BadgeCheckIcon, left: "22.7%", top: "77.2%", visibility: "flex", delay: 0.4, duration: 7.5 },
  { label: "تایم‌لاین بالینی", icon: HistoryIcon, left: "65.8%", top: "85.8%", visibility: "hidden lg:flex", delay: 2.2, duration: 6.2 },
  { label: "بینش بالینی", icon: SparklesIcon, left: "30%", top: "14.2%", emphasized: true, visibility: "hidden lg:flex", delay: 1.2, duration: 6.8 },
];

function IntelligenceCore() {
  const reduce = useReducedMotion();
  return (
    <div className="relative mx-auto aspect-square w-[300px] sm:w-[440px] lg:w-[620px]">
      {/* rings, halo, core, dots and medical markers — exact Pen geometry */}
      <svg viewBox="0 0 600 600" className="absolute inset-0 h-full w-full" aria-hidden="true">
        {/* subtle outer halo */}
        <circle cx="300" cy="300" r="250" fill="var(--brand-soft)" opacity="0.5" />
        {/* concentric orbital rings */}
        <circle cx="300" cy="300" r="260" stroke="var(--brand-border)" strokeWidth="1.5" fill="none" />
        <circle cx="300" cy="300" r="200" stroke="var(--brand-border)" strokeWidth="1" fill="none" opacity="0.8" />
        <circle cx="300" cy="300" r="140" stroke="var(--brand-border)" strokeWidth="1" fill="none" opacity="0.5" />
        {/* core glow + teal core */}
        <circle cx="300" cy="300" r="110" fill="var(--brand-soft)" opacity="0.8" />
        <circle cx="300" cy="300" r="95" fill="var(--brand)" opacity="0.12" />
        <circle cx="300" cy="300" r="80" fill="var(--brand)" />
        {/* orbital dots */}
        <circle cx="280" cy="40" r="6" fill="var(--brand)" />
        <circle cx="39" cy="299" r="5" fill="var(--brand-strong)" />
        <circle cx="538" cy="234" r="4" fill="var(--brand)" opacity="0.7" />
        <circle cx="184" cy="560" r="4" fill="var(--success)" />
        <circle cx="123" cy="123" r="3" fill="var(--brand)" opacity="0.5" />
        {/* medical plus markers */}
        <g stroke="var(--brand-border)" strokeWidth="3" strokeLinecap="round">
          <path d="M472 127h14M479 120v14" />
          <path d="M96 458h12M102 452v12" />
        </g>
      </svg>

      {/* AI brain at the core center */}
      <span className="absolute inset-0 m-auto flex size-9 items-center justify-center sm:size-12 lg:size-14">
        <BrainIcon className="size-full text-primary-foreground" />
      </span>

      {/* floating record chips orbiting the core (Pen positions) */}
      {CHIPS.map((chip) => (
        <div
          key={chip.label}
          className={`absolute -translate-x-1/2 -translate-y-1/2 scale-[0.85] sm:scale-90 lg:scale-100 ${chip.visibility}`}
          style={{ left: chip.left, top: chip.top }}
        >
          <motion.div
            className={`flex h-10.5 items-center gap-2 rounded-[10px] border bg-card px-3 shadow-[0_6px_16px_#1C2B2A14] ${
              chip.emphasized ? "border-brand-border" : "border-border"
            }`}
            animate={reduce ? undefined : { y: [0, -7, 0] }}
            transition={{ duration: chip.duration, repeat: Infinity, ease: "easeInOut", delay: chip.delay }}
          >
            <span
              className={`flex size-6.5 items-center justify-center rounded-lg ${
                chip.emphasized ? "bg-brand text-primary-foreground" : "bg-brand-soft text-brand"
              }`}
            >
              <chip.icon className="size-3.5" />
            </span>
            <span className={`text-xs whitespace-nowrap ${chip.emphasized ? "font-semibold text-brand" : "font-medium text-foreground"}`}>
              {chip.label}
            </span>
          </motion.div>
        </div>
      ))}
    </div>
  );
}

/** Phase 4 landing hero — text on the LEFT, intelligence core on the RIGHT. */
export function Hero() {
  const reduce = useReducedMotion();
  const entrance = (delay: number) =>
    reduce
      ? {}
      : {
          initial: { opacity: 0, y: 20 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.6, delay, ease: [0.21, 0.47, 0.32, 0.98] as const },
        };

  return (
    <section className="relative overflow-x-clip">
      <div className="mx-auto flex w-full max-w-[1440px] flex-col items-center gap-10 px-6 py-14 lg:min-h-[calc(100svh-4.25rem)] lg:flex-row lg:items-center lg:gap-12 lg:px-16 lg:py-10">
        {/* intelligence core — first in DOM: RIGHT on desktop (RTL), above text on mobile */}
        <motion.div data-reveal-safe="" className="w-full shrink-0 lg:w-[46%]" {...entrance(0.25)}>
          <IntelligenceCore />
        </motion.div>

        {/* text — LEFT on desktop, below the core on mobile (RTL end) */}
        <motion.div data-reveal-safe="" className="flex w-full flex-col items-center gap-6 text-center lg:w-[54%] lg:items-end lg:text-right" {...entrance(0)}>
          <span className="inline-flex h-7.5 items-center rounded-full bg-brand-soft px-3.5 text-xs font-semibold text-brand">
            برای پزشکان و تیم‌های بالینی
          </span>
          <h1 className="text-[26px] leading-[1.4] font-extrabold tracking-tight sm:text-[34px] lg:text-[44px]">
            برای تصمیم‌های بهتر بالینی
            <br />
            دستیار هوشمند پزشک
          </h1>
          <p className="max-w-[480px] text-[15px] leading-8 text-muted-foreground lg:text-base">
            Clinical AI Copilot اطلاعات پراکندهٔ بیمار را به بینش‌های قابل استفادهٔ
            پزشکی تبدیل می‌کند.
          </p>
          <div className="flex w-full flex-col items-center gap-3.5 sm:w-auto sm:flex-row">
            <Link
              href="/login"
              className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-[10px] bg-brand px-7 text-[15px] font-semibold text-primary-foreground shadow-[0_8px_20px_#0F766E26] transition-colors hover:bg-brand-strong sm:w-auto"
            >
              مشاهده دمو
              <PlayIcon className="size-4" />
            </Link>
            <Link
              href="/login"
              className="inline-flex h-12 w-full items-center justify-center rounded-[10px] border bg-card px-7 text-[15px] font-medium transition-colors hover:bg-surface-2 sm:w-auto"
            >
              شروع استفاده
            </Link>
          </div>
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <ShieldCheckIcon className="size-3.5 text-brand" />
            ابزار کمک به تصمیم‌گیری پزشک — نه جایگزین او
          </p>
        </motion.div>
      </div>
    </section>
  );
}
