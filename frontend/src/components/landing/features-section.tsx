"use client";

import { ClipboardListIcon, PillIcon, SparklesIcon, ZapIcon } from "lucide-react";

import { Reveal } from "./reveal";

const FEATURES = [
  {
    icon: ClipboardListIcon,
    title: "خلاصهٔ هوشمند پرونده",
    description:
      "وضعیت بیمار را در چند ثانیه مرور کنید — مشکلات، آلرژی‌ها، داروها و آزمایش‌ها در یک نگاه.",
  },
  {
    icon: PillIcon,
    title: "دستیار دارویی",
    description:
      "بررسی ایمنی دارو و تداخل‌ها بر اساس پروندهٔ واقعی بیمار، پیش از هر نسخه.",
  },
  {
    icon: ZapIcon,
    title: "دسترسی سریع به اطلاعات",
    description:
      "یافتن پاسخ در میان اسناد و نتایج، به‌جای جست‌وجوی دستی در پرونده‌های طولانی.",
  },
  {
    icon: SparklesIcon,
    title: "دستیار هوشمند بالینی",
    description:
      "پرسش دربارهٔ بیمار و دریافت پاسخ همراه با ارجاع به منبع — تصمیم با پزشک.",
  },
];

/** Phase 4 features — exactly four core capabilities. */
export function FeaturesSection() {
  return (
    <section id="features" className="scroll-mt-20 bg-background">
      <div className="mx-auto flex w-full max-w-[1200px] flex-col items-center gap-12 px-6 py-22 lg:px-0">
        <Reveal className="flex flex-col items-center gap-3 text-center">
          <p className="text-[13px] font-semibold text-brand">امکانات</p>
          <h2 className="text-[26px] font-bold sm:text-[32px]">
            چهار قابلیت اصلی، برای کار روزمرهٔ بالینی
          </h2>
        </Reveal>
        <div className="grid w-full grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((feature, index) => (
            <Reveal key={feature.title} delay={index * 0.1}>
              <div className="flex h-full flex-col gap-3 rounded-2xl border bg-card p-5">
                <span className="flex size-11 items-center justify-center rounded-xl bg-brand-soft text-brand">
                  <feature.icon className="size-5" />
                </span>
                <div className="space-y-2">
                  <h3 className="text-base font-bold">{feature.title}</h3>
                  <p className="text-[13px] leading-7 text-muted-foreground">
                    {feature.description}
                  </p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
