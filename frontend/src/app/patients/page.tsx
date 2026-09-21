import Link from "next/link";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { SearchIcon, SearchXIcon, UsersIcon, XIcon } from "lucide-react";

import { AddPatientButton } from "@/components/patients/patient-actions";
import {
  PatientListRow,
  type PatientRowStatus,
} from "@/components/patients/patient-list-row";
import { PatientListPagination } from "@/components/patients/patient-list-pagination";
import { AppShell } from "@/components/shared/app-shell";
import { ErrorState } from "@/components/shared/error-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import { faNum } from "@/lib/format";
import type { Patient } from "@/lib/types";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 20;

export const metadata = { title: "بیماران" };

interface PatientsPageProps {
  searchParams: Promise<{ q?: string; page?: string }>;
}

/**
 * Clinical status chips (severe allergy / active medications / recorded
 * problems) come from the EXISTING per-patient overview endpoint — no
 * backend change, no fabricated data. A failed overview just renders that
 * row without chips; the directory itself still works.
 */
async function loadRowStatuses(
  patients: Patient[]
): Promise<Map<number, PatientRowStatus>> {
  const entries = await Promise.all(
    patients.map(async (patient) => {
      try {
        const overview = await api.getPatientOverview(patient.id);
        const status: PatientRowStatus = {
          severeAllergy: overview.allergies.some(
            (allergy) => allergy.severity === "severe"
          ),
          activeMedications: overview.active_medications.length,
          recordedProblems: overview.conditions.length,
        };
        return [patient.id, status] as const;
      } catch {
        return [patient.id, null] as const;
      }
    })
  );
  return new Map(
    entries.filter((entry): entry is readonly [number, PatientRowStatus] => {
      return entry[1] != null;
    })
  );
}

/** Pen empty-state block — compact, calm, no illustration. */
function EmptyBlock({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: typeof UsersIcon;
  title: string;
  description: string;
  action: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2.5 rounded-xl border bg-card px-8 py-10 text-center">
      <span className="flex size-11 items-center justify-center rounded-full bg-surface-2">
        <Icon className="size-5 text-muted-foreground" />
      </span>
      <p className="text-base font-semibold">{title}</p>
      <p className="max-w-[320px] text-[13px] leading-6 text-muted-foreground">
        {description}
      </p>
      <div className="mt-1.5">{action}</div>
    </div>
  );
}

export default async function PatientsPage({ searchParams }: PatientsPageProps) {
  const params = await searchParams;
  const query = (params.q ?? "").trim();
  const page = Math.max(1, Number(params.page) || 1);

  let data: Awaited<ReturnType<typeof api.listPatients>> | null = null;
  let errorMessage: string | null = null;
  try {
    data = await api.listPatients({
      q: query || undefined,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    });
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 401) {
      redirect("/login");
    }
    errorMessage = cause instanceof ApiError ? cause.message : "خطای ناشناخته";
  }

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const items = data?.items ?? [];
  const statuses =
    data && items.length > 0 ? await loadRowStatuses(items) : new Map<number, PatientRowStatus>();
  const isEmpty = data != null && items.length === 0 && total === 0;

  return (
    <div className="flex min-h-svh flex-1 flex-col">
      <AppShell />
      <main className="mx-auto w-full max-w-[1160px] flex-1 px-4 py-7 xl:px-0">
        {/* page header */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="min-w-0 space-y-1">
            <div className="flex items-center gap-2.5">
              <h1 className="text-[22px] leading-8 font-bold">بیماران</h1>
              {data && !errorMessage ? (
                <span className="inline-flex h-[22px] items-center rounded-md bg-surface-2 px-2 text-xs font-medium text-muted-foreground tabular-nums">
                  {faNum(total)} بیمار
                </span>
              ) : null}
            </div>
            <p className="text-[13px] text-muted-foreground">
              مدیریت و دسترسی سریع به پروندهٔ بیماران
            </p>
          </div>
          <AddPatientButton />
        </div>

        {/* search */}
        <form action="/patients" className="mt-4">
          <div className="relative">
            <SearchIcon className="absolute start-4 top-1/2 size-[17px] -translate-y-1/2 text-faint" />
            <Input
              name="q"
              defaultValue={query}
              placeholder="جست‌وجوی بیمار با نام، کد ملی یا شماره تماس"
              aria-label="جست‌وجوی بیمار"
              className="h-[46px] rounded-[10px] bg-card ps-12 pe-12 text-sm"
            />
            {query ? (
              <Link
                href="/patients"
                aria-label="پاک کردن جست‌وجو"
                title="پاک کردن جست‌وجو"
                className="absolute end-3 top-1/2 flex size-[22px] -translate-y-1/2 items-center justify-center rounded-full bg-surface-2 text-muted-foreground transition-colors hover:text-foreground"
              >
                <XIcon className="size-3" />
              </Link>
            ) : null}
          </div>
        </form>

        {/* body */}
        <div className="mt-4 space-y-4">
          {errorMessage ? (
            <ErrorState message={errorMessage} />
          ) : data == null ? null : isEmpty && !query ? (
            <EmptyBlock
              icon={UsersIcon}
              title="هنوز بیماری ثبت نشده است"
              description="برای شروع، اولین بیمار را به پرونده‌های خود اضافه کنید."
              action={<AddPatientButton />}
            />
          ) : isEmpty && query ? (
            <EmptyBlock
              icon={SearchXIcon}
              title="بیماری با این مشخصات پیدا نشد"
              description="نتیجه‌ای برای جست‌وجوی شما وجود ندارد."
              action={
                <Button
                  size="lg"
                  className="gap-1.5 px-4"
                  render={<Link href="/patients" />}
                >
                  پاک کردن جست‌وجو
                  <XIcon className="size-3.5" />
                </Button>
              }
            />
          ) : (
            <>
              {query ? (
                <p className="text-[13px] text-muted-foreground">
                  نتایج جست‌وجو برای «{query}» — {faNum(total)} بیمار
                </p>
              ) : null}
              <div className="overflow-hidden rounded-xl border bg-card">
                <ul>
                  {items.map((patient) => (
                    <PatientListRow
                      key={patient.id}
                      patient={patient}
                      status={statuses.get(patient.id)}
                    />
                  ))}
                </ul>
              </div>
              <PatientListPagination
                page={page}
                totalPages={totalPages}
                total={total}
                query={query}
              />
            </>
          )}
        </div>
      </main>
    </div>
  );
}
