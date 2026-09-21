/** Minimal landing footer — one quiet line (Phase 4 Pen). */
export function LandingFooter() {
  return (
    <footer className="border-t bg-card">
      <div className="mx-auto flex h-16 w-full max-w-[1440px] flex-wrap items-center justify-between gap-3 px-6 lg:px-16">
        <div className="flex items-center gap-5 text-xs text-muted-foreground">
          <span>حریم خصوصی</span>
          <span>شرایط استفاده</span>
          <span>تماس با ما</span>
        </div>
        <p className="text-xs text-muted-foreground">
          © ۱۴۰۵ Clinical AI Copilot — دستیار هوشمند بالینی پزشک
        </p>
      </div>
    </footer>
  );
}
