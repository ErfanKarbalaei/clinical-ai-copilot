"use client";

import { BrainIcon, ChevronLeftIcon, DatabaseIcon, LightbulbIcon } from "lucide-react";

import { Reveal } from "./reveal";

const STEPS = [
  {
    icon: DatabaseIcon,
    title: "داده‌های بیمار",
    description: "پرونده، آزمایش، دارو و سند — همه در یک جا",
    emphasized: false,
  },
  {
    icon: BrainIcon,
    title: "موتور بالینی هوشمند",
    description: "تحلیل و ارتباط اطلاعات با ذکر منبع",
    emphasized: true,
  },
  {
    icon: LightbulbIcon,
    title: "بینش بالینی",
    description: "خلاصه و هشدارهای قابل اقدام برای پزشک",
    emphasized: false,
  },
];

/** Phase 4 "how it works" — three-step RTL flow (data → engine → insight). */
export function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-20 bg-background">
      <div className="mx-auto flex w-full max-w-[1200px] flex-col items-center gap-14 px-6 py-22 lg:px-0">
        <Reveal className="flex flex-col items-center gap-3 text-center">
          <p className="text-[13px] font-semibold text-brand">چطور کار می‌کند</p>
          <h2 className="text-[26px] font-bold sm:text-[32px]">از داده تا بینش، در سه گام</h2>
        </Reveal>

        <div className="flex w-full flex-col items-center justify-center gap-2 lg:flex-row lg:items-start">
          {STEPS.map((step, index) => (
            <div key={step.title} className="flex flex-col items-center gap-2 lg:contents">
              <Reveal delay={index * 0.15} className="flex w-[280px] flex-col items-center gap-3.5">
                <span
                  className={`flex size-[88px] items-center justify-center rounded-full border ${
                    step.emphasized
                      ? "border-transparent bg-brand text-primary-foreground shadow-[0_10px_24px_#0F766E33]"
                      : "border-brand-border bg-card text-brand"
                  }`}
                >
                  <step.icon className="size-8" />
                </span>
                <div className="space-y-1.5 text-center">
                  <h3 className="text-[17px] font-bold">{step.title}</h3>
                  <p className="text-[13px] leading-7 text-muted-foreground">
                    {step.description}
                  </p>
                </div>
              </Reveal>
              {index < STEPS.length - 1 ? (
                <Reveal
                  delay={index * 0.15 + 0.1}
                  className="flex -rotate-90 items-center pb-16 lg:rotate-0 lg:pb-0 lg:pt-[34px]"
                  y={0}
                >
                  <ChevronLeftIcon className="size-5 text-brand-border" />
                  <ChevronLeftIcon className="-ms-3 size-5 text-brand-border/50" />
                </Reveal>
              ) : null}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
