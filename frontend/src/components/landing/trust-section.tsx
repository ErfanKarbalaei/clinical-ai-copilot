"use client";

import { BadgeCheckIcon, ClipboardCheckIcon, ShieldCheckIcon, StethoscopeIcon } from "lucide-react";

import { Reveal } from "./reveal";

const PILLARS = [
  { icon: ClipboardCheckIcon, label: "پاسخ‌ها مبتنی بر پروندهٔ واقعی" },
  { icon: BadgeCheckIcon, label: "ذکر منبع برای هر پاسخ" },
  { icon: StethoscopeIcon, label: "مسئولیت نهایی با پزشک" },
];

/** Phase 4 trust section — AI as decision support, never a replacement. */
export function TrustSection() {
  return (
    <section id="trust" className="scroll-mt-20 bg-card">
      <div className="mx-auto flex w-full max-w-[860px] flex-col items-center gap-7 px-6 py-24 text-center">
        <Reveal>
          <span className="flex size-16 items-center justify-center rounded-full bg-brand-soft text-brand">
            <ShieldCheckIcon className="size-7" />
          </span>
        </Reveal>
        <Reveal delay={0.1}>
          <h2 className="text-[22px] leading-[1.6] font-bold sm:text-[26px]">
            هوش مصنوعی، ابزارِ کمک به تصمیم‌گیری است — نه جایگزین پزشک
          </h2>
        </Reveal>
        <Reveal delay={0.2}>
          <p className="max-w-[620px] text-[15px] leading-9 text-muted-foreground">
            Clinical AI Copilot فقط بر اساس اطلاعات واقعی پروندهٔ بیمار پاسخ
            می‌دهد، هر پاسخ را به منبع آن گره می‌زند و تصمیم نهایی و مسئولیت
            آن همیشه با پزشک است.
          </p>
        </Reveal>
        <Reveal delay={0.3} className="flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
          {PILLARS.map((pillar) => (
            <span key={pillar.label} className="flex items-center gap-2 text-[13px] font-medium text-muted-foreground">
              <pillar.icon className="size-4 text-brand" />
              {pillar.label}
            </span>
          ))}
        </Reveal>
      </div>
    </section>
  );
}
