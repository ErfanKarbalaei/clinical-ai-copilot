import Link from "next/link";
import { ChevronLeftIcon, ChevronRightIcon, SearchIcon, UsersIcon } from "lucide-react";

import { AddPatientButton } from "@/components/patients/patient-actions";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError, api } from "@/lib/api";
import { calculateAge, formatDate, genderLabels } from "@/lib/format";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 20;

export const metadata = { title: "بیماران" };

interface PatientsPageProps {
  searchParams: Promise<{ q?: string; page?: string }>;
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
    errorMessage = cause instanceof ApiError ? cause.message : "خطای ناشناخته";
  }

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  function pageHref(targetPage: number): string {
    const search = new URLSearchParams();
    if (query) search.set("q", query);
    if (targetPage > 1) search.set("page", String(targetPage));
    const qs = search.toString();
    return qs ? `/patients?${qs}` : "/patients";
  }

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 space-y-6 px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold">بیماران</h1>
          <p className="text-sm text-muted-foreground">
            {query
              ? `نتایج جست‌وجو برای «${query}» — ${total} بیمار`
              : `در مجموع ${total} بیمار ثبت شده است`}
          </p>
        </div>
        <AddPatientButton />
      </div>

      <Card>
        <CardHeader>
          <form action="/patients" className="flex w-full items-center gap-2">
            <div className="relative flex-1">
              <SearchIcon className="absolute end-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                name="q"
                defaultValue={query}
                placeholder="جست‌وجو بر اساس نام، نام خانوادگی یا کد ملی…"
                className="pe-8"
              />
            </div>
            <Button type="submit" variant="outline">
              جست‌وجو
            </Button>
            {query ? (
              <Button type="button" variant="ghost" render={<Link href="/patients" />}>
                پاک‌کردن
              </Button>
            ) : null}
          </form>
        </CardHeader>
        <CardContent>
          {errorMessage ? (
            <ErrorState message={errorMessage} />
          ) : data && data.items.length === 0 ? (
            <EmptyState
              icon={UsersIcon}
              title="بیماری یافت نشد"
              description={
                query
                  ? "هیچ بیماری با این عبارت جست‌وجو مطابقت ندارد."
                  : "با دکمهٔ «بیمار جدید» نخستین بیمار را ثبت کنید."
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>بیمار</TableHead>
                  <TableHead>سن</TableHead>
                  <TableHead>جنسیت</TableHead>
                  <TableHead>تاریخ تولد</TableHead>
                  <TableHead>شماره تماس</TableHead>
                  <TableHead className="text-end">عملیات</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(data?.items ?? []).map((patient) => {
                  const age = calculateAge(patient.date_of_birth);
                  return (
                    <TableRow key={patient.id}>
                      <TableCell>
                        <div className="flex flex-col">
                          <Link
                            href={`/patients/${patient.id}`}
                            className="font-medium hover:underline"
                          >
                            {patient.first_name} {patient.last_name}
                          </Link>
                          {patient.national_code ? (
                            <span dir="ltr" className="font-mono text-xs text-muted-foreground">
                              {patient.national_code}
                            </span>
                          ) : null}
                        </div>
                      </TableCell>
                      <TableCell>
                        {age === null ? "—" : `${age} سال`}
                      </TableCell>
                      <TableCell>{genderLabels[patient.gender]}</TableCell>
                      <TableCell>{formatDate(patient.date_of_birth)}</TableCell>
                      <TableCell dir="ltr" className="font-mono text-xs">
                        {patient.phone ?? "—"}
                      </TableCell>
                      <TableCell className="text-end">
                        <Button
                          variant="outline"
                          size="sm"
                          render={<Link href={`/patients/${patient.id}`} />}
                        >
                          مشاهدهٔ پرونده
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}

          {data && totalPages > 1 ? (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                صفحهٔ {page} از {totalPages}
              </p>
              <div className="flex items-center gap-2">
                {page > 1 ? (
                  <Button variant="outline" size="sm" render={<Link href={pageHref(page - 1)} />}>
                    <ChevronRightIcon />
                    قبلی
                  </Button>
                ) : null}
                {page < totalPages ? (
                  <Button variant="outline" size="sm" render={<Link href={pageHref(page + 1)} />}>
                    بعدی
                    <ChevronLeftIcon />
                  </Button>
                ) : null}
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </main>
  );
}
