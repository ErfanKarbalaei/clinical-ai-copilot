import { Skeleton } from "@/components/shared/skeleton";

export default function PatientLoading() {
  return (
    <main className="mx-auto w-full max-w-7xl flex-1 space-y-6 px-4 py-8">
      <Skeleton className="h-8 w-44" />
      <Skeleton className="h-32 w-full" />
      <div className="grid gap-6 xl:grid-cols-12">
        <div className="space-y-6 xl:col-span-8">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
        <div className="order-first xl:order-last xl:col-span-4">
          <Skeleton className="h-96 w-full" />
        </div>
      </div>
    </main>
  );
}
