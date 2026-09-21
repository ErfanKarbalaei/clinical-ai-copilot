import { AppShell } from "@/components/shared/app-shell";

/** Phase 3 directory skeleton — mirrors the real row structure (7 × ~84px
 * rows with varied bar widths) without any fake patient content. */
export default function PatientsLoading() {
  const barWidths = [150, 120, 165, 135, 150, 110, 160];
  const statusWidths = [190, 165, 210, 190, 240, 165, 210];
  const bars =
    "animate-pulse rounded-full bg-muted";
  const chips = "animate-pulse rounded-md bg-muted";

  return (
    <div className="flex min-h-svh flex-1 flex-col">
      <AppShell />
      <main className="mx-auto w-full max-w-[1160px] flex-1 px-4 py-7 xl:px-0">
        {/* header skeleton */}
        <div className="flex items-center justify-between gap-4">
          <div className="space-y-2">
            <div className={`h-7 w-32 ${bars}`} />
            <div className={`h-4 w-64 ${bars}`} />
          </div>
          <div className={`h-9 w-32 rounded-lg ${chips}`} />
        </div>

        {/* search skeleton */}
        <div
          className={`mt-4 h-[46px] w-full rounded-[10px] ${chips}`}
          aria-hidden="true"
        />

        {/* rows skeleton */}
        <div className="mt-4 overflow-hidden rounded-xl border bg-card">
          {barWidths.map((nameWidth, index) => (
            <div
              key={index}
              className="flex min-h-[84px] items-center gap-4 border-b border-border/50 px-4 last:border-0"
              aria-hidden="true"
            >
              <div className="flex min-w-0 flex-1 items-center gap-3">
                <div className={`size-10 shrink-0 rounded-full ${chips}`} />
                <div className="space-y-2">
                  <div className={`h-3.5 ${bars}`} style={{ width: nameWidth }} />
                  <div className={`h-2.5 w-24 ${bars}`} />
                </div>
              </div>
              <div className="hidden shrink-0 flex-col gap-1.5 xl:flex">
                <div className={`h-2.5 w-[110px] ${bars}`} />
                <div className={`h-2.5 w-[120px] ${bars}`} />
              </div>
              <div className="hidden shrink-0 xl:block">
                <div className={`h-2.5 w-[100px] ${bars}`} />
              </div>
              <div className="hidden shrink-0 sm:block">
                <div
                  className={`h-[26px] ${chips}`}
                  style={{ width: statusWidths[index] }}
                />
              </div>
              <div className={`h-9 w-[110px] shrink-0 rounded-lg ${chips}`} />
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
