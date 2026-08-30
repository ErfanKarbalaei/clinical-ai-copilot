"use client";

import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { LoaderIcon, SendIcon, SparklesIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import type { ChatTurn } from "@/lib/types";

const MAX_QUESTION_LENGTH = 2000;

/** AI assistant section — grounded in THIS patient's structured context. */
export function ClinicalChat({ patientId }: { patientId: number }) {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // keep the newest message in view
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [turns, loading]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    setQuestion("");
    setError(null);
    setTurns((previous) => [...previous, { role: "user", content: trimmed }]);
    setLoading(true);

    try {
      const history = turns.slice(-6);
      const response = await api.askClinicalQuestion(
        patientId,
        trimmed,
        history
      );
      setTurns((previous) => [
        ...previous,
        { role: "assistant", content: response.answer },
      ]);
    } catch (cause) {
      setError(
        cause instanceof ApiError ? cause.message : "خطای ناشناخته رخ داد."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <SparklesIcon className="size-4 text-muted-foreground" />
          دستیار هوشمند بالینی
        </CardTitle>
        <CardDescription>
          پرسش شما دربارهٔ همین بیمار — پاسخ‌ها فقط بر اساس اطلاعات ثبت‌شدهٔ
          پرونده ساخته می‌شوند.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div
          ref={listRef}
          className="max-h-96 space-y-3 overflow-y-auto scroll-smooth"
        >
          {turns.length === 0 && !loading ? (
            <p className="rounded-lg bg-muted/50 px-4 py-6 text-center text-sm text-muted-foreground">
              از وضعیت بیمار بپرسید — مثلاً: «خلاصهٔ وضعیت بالینی بیمار چیست؟»
              یا «کدام داروها با حساسیت ثبت‌شده تداخل احتمالی دارند؟»
            </p>
          ) : null}

          {turns.map((turn, index) => (
            <div
              key={index}
              className={
                turn.role === "user"
                  ? "ms-auto max-w-[85%] rounded-lg bg-primary/10 px-3 py-2 text-sm leading-6"
                  : "max-w-[95%] rounded-lg border bg-background px-3 py-2 text-sm leading-7"
              }
            >
              {turn.role === "user" ? (
                turn.content
              ) : (
                <p className="whitespace-pre-wrap">{turn.content}</p>
              )}
            </div>
          ))}

          {loading ? (
            <p className="flex items-center gap-2 px-1 text-sm text-muted-foreground">
              <LoaderIcon className="size-4 animate-spin" />
              در حال بررسی پرونده و پردازش پاسخ…
            </p>
          ) : null}
        </div>

        {error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : null}

        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          <Textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="پرسش خود را دربارهٔ بیمار بنویسید…"
            rows={2}
            maxLength={MAX_QUESTION_LENGTH}
            disabled={loading}
            className="flex-1 resize-none"
            dir="rtl"
          />
          <Button
            type="submit"
            size="lg"
            disabled={loading || question.trim() === ""}
            aria-label="ارسال پرسش"
          >
            {loading ? (
              <LoaderIcon className="animate-spin" />
            ) : (
              <SendIcon className="rtl:-scale-x-100" />
            )}
            ارسال
          </Button>
        </form>

        <p className="text-center text-xs leading-6 text-muted-foreground">
          این پاسخ‌ها فقط ابزار کمک به تصمیم‌گیری‌اند و ممکن است ناقص یا
          نادرست باشند؛ تصمیم نهایی و مسئولیت آن همیشه با پزشک است.
        </p>
      </CardContent>
    </Card>
  );
}
