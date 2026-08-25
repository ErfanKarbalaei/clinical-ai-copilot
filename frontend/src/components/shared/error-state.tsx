"use client";

import { useRouter } from "next/navigation";
import { RotateCcwIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  title?: string;
  message: string;
}

/** Persian error block with a retry button (re-runs the server component). */
export function ErrorState({
  title = "خطا در دریافت اطلاعات",
  message,
}: ErrorStateProps) {
  const router = useRouter();

  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-12 text-center">
      <p className="font-medium text-destructive">{title}</p>
      <p className="text-sm text-muted-foreground">{message}</p>
      <Button variant="outline" size="sm" onClick={() => router.refresh()}>
        <RotateCcwIcon />
        تلاش مجدد
      </Button>
    </div>
  );
}
