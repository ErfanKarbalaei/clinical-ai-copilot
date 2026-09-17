"use client";

import { useRouter } from "next/navigation";
import { LogOutIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { clearToken } from "@/lib/auth";

/** Clear the session and return to the login page. */
export function LogoutButton() {
  const router = useRouter();
  return (
    <Button
      variant="ghost"
      size="sm"
      className="gap-1.5"
      onClick={() => {
        clearToken();
        router.push("/login");
        router.refresh();
      }}
    >
      <LogOutIcon />
      خروج
    </Button>
  );
}
