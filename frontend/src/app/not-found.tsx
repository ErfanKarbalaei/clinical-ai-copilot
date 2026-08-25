import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center">
      <p className="font-heading text-5xl font-bold text-muted-foreground/60" dir="ltr">
        404
      </p>
      <h1 className="text-xl font-bold">صفحه یا مورد درخواستی یافت نشد</h1>
      <p className="text-sm text-muted-foreground">
        ممکن است آدرس نادرست باشد یا این مورد حذف شده باشد.
      </p>
      <Button render={<Link href="/patients" />}>بازگشت به فهرست بیماران</Button>
    </main>
  );
}
