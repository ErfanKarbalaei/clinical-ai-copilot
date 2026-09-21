import type { Metadata } from "next";

import { FeaturesSection } from "@/components/landing/features-section";
import { FinalCta } from "@/components/landing/final-cta";
import { Hero } from "@/components/landing/hero";
import { HowItWorks } from "@/components/landing/how-it-works";
import { LandingFooter } from "@/components/landing/landing-footer";
import { LandingNav } from "@/components/landing/landing-nav";
import { ProblemSection } from "@/components/landing/problem-section";
import { ProductPreview } from "@/components/landing/product-preview";
import { TrustSection } from "@/components/landing/trust-section";

export const metadata: Metadata = {
  title: "دستیار هوشمند بالینی پزشک",
  description:
    "Clinical AI Copilot اطلاعات پراکندهٔ بیمار را به بینش‌های قابل استفادهٔ پزشکی تبدیل می‌کند — ابزار کمک به تصمیم‌گیری پزشک، نه جایگزین او.",
};

/** Public landing page (Phase 4) — the clinical product story in Persian RTL. */
export default function HomePage() {
  return (
    <div className="flex min-h-svh flex-1 flex-col overflow-x-clip bg-card">
      <LandingNav />
      <main className="flex-1">
        <Hero />
        <ProblemSection />
        <HowItWorks />
        <ProductPreview />
        <FeaturesSection />
        <TrustSection />
        <FinalCta />
      </main>
      <LandingFooter />
    </div>
  );
}
