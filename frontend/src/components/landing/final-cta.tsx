"use client";

import Link from "next/link";

import { Reveal } from "./reveal";

/** Phase 4 final CTA — deep clinical teal panel with the primary action. */
export function FinalCta() {
  return (
    <section className="bg-card pb-24">
      <div className="mx-auto w-full max-w-[1200px] px-6">
        <Reveal>
          <div className="flex flex-col items-center gap-6 rounded-3xl bg-brand-strong px-6 py-16 text-center shadow-[0_24px_60px_#0B5D5733] sm:px-20">
            <h2 className="max-w-[640px] text-[22px] leading-[1.6] font-bold text-primary-foreground sm:text-[28px]">
              آماده‌اید تجربهٔ جدیدی از مدیریت پروندهٔ پزشکی را ببینید؟
            </h2>
            <p className="text-[15px] text-primary-foreground/70">
              در چند دقیقه نخستین بیمار خود را ثبت کنید و دستیار بالینی را در
              کنار پرونده ببینید.
            </p>
            <Link
              href="/login"
              className="inline-flex h-12.5 items-center rounded-[10px] bg-card px-8 text-[15px] font-semibold text-brand-strong transition-transform hover:-translate-y-0.5"
            >
              مشاهده نسخه آزمایشی
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
