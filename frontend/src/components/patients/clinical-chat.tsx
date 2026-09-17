"use client";

import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  ActivityIcon,
  AlertCircleIcon,
  ExternalLinkIcon,
  FileTextIcon,
  FlaskConicalIcon,
  LoaderIcon,
  MicIcon,
  PillIcon,
  PlusIcon,
  SendIcon,
  ShieldAlertIcon,
  SparklesIcon,
  Trash2Icon,
} from "lucide-react";

import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import type { ConversationSummary, EvidenceItem } from "@/lib/types";

const MAX_QUESTION_LENGTH = 2000;

/** One rendered chat turn — assistant turns may carry validated evidence. */
interface RenderedTurn {
  role: "user" | "assistant";
  content: string;
  evidence?: EvidenceItem[];
}

function evidenceIcon(sourceType: EvidenceItem["source_type"]) {
  switch (sourceType) {
    case "medication":
      return <PillIcon className="size-3.5 shrink-0 text-muted-foreground" />;
    case "allergy":
      return (
        <AlertCircleIcon className="size-3.5 shrink-0 text-muted-foreground" />
      );
    case "lab":
      return (
        <FlaskConicalIcon className="size-3.5 shrink-0 text-muted-foreground" />
      );
    case "document":
    case "clinical_note":
      return <FileTextIcon className="size-3.5 shrink-0 text-muted-foreground" />;
    case "voice_note":
      return <MicIcon className="size-3.5 shrink-0 text-muted-foreground" />;
    default:
      return <ActivityIcon className="size-3.5 shrink-0 text-muted-foreground" />;
  }
}

/** AI assistant section — persisted conversations grounded in THIS patient's context. */
export function ClinicalChat({ patientId }: { patientId: number }) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [turns, setTurns] = useState<RenderedTurn[]>([]);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // explicit UI affordance (no keyword detection): when on, the message is
  // answered with the specialized medication-safety prompt (Task 14)
  const [safetyMode, setSafetyMode] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // load the patient's previous conversations (most recently updated first)
    let cancelled = false;
    (async () => {
      try {
        const items = await api.listConversations(patientId);
        if (cancelled) return;
        setConversations(items);
        if (items.length > 0) {
          setActiveId(items[0].id);
          const detail = await api.getConversation(items[0].id);
          if (cancelled) return;
          setTurns(
            detail.messages.map((message) => ({
              role: message.role,
              content: message.content,
              evidence: message.evidence ?? undefined,
            }))
          );
        }
      } catch {
        if (!cancelled) setError("بارگذاری گفتگوها با خطا مواجه شد.");
      } finally {
        if (!cancelled) setLoadingConversations(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  useEffect(() => {
    // keep the newest message in view
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [turns, loading]);

  async function selectConversation(conversationId: number) {
    if (loading) return;
    setActiveId(conversationId);
    setTurns([]);
    setError(null);
    try {
      const detail = await api.getConversation(conversationId);
      setTurns(
        detail.messages.map((message) => ({
          role: message.role,
          content: message.content,
          evidence: message.evidence ?? undefined,
        }))
      );
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "خطای ناشناخته رخ داد.");
    }
  }

  async function handleNewConversation() {
    if (loading) return;
    try {
      const conversation = await api.createConversation(patientId);
      setConversations((previous) => [conversation, ...previous]);
      setActiveId(conversation.id);
      setTurns([]);
      setError(null);
      setQuestion("");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "ساخت گفتگو با خطا مواجه شد.");
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    setQuestion("");
    setError(null);
    setTurns((previous) => [...previous, { role: "user", content: trimmed }]);
    setLoading(true);

    try {
      // continue the active conversation (create one implicitly if none)
      let conversationId = activeId;
      if (conversationId == null) {
        const conversation = await api.createConversation(patientId);
        conversationId = conversation.id;
        setActiveId(conversationId);
        setConversations((previous) => [conversation, ...previous]);
      }

      const response = await api.sendConversationMessage(conversationId, {
        content: trimmed,
        medication_safety: safetyMode,
      });

      setTurns((previous) => [
        ...previous,
        {
          role: "assistant",
          content: response.assistant_message.content,
          evidence: response.assistant_message.evidence ?? undefined,
        },
      ]);
      // keep the selector ordered by latest activity (matching the backend)
      api
        .listConversations(patientId)
        .then(setConversations)
        .catch(() => undefined);
    } catch (cause) {
      // the user message may already be persisted server-side (502) — it
      // will reappear on reload; keep the input so nothing is lost visually
      setTurns((previous) => previous.slice(0, -1));
      setQuestion(trimmed);
      setError(
        cause instanceof ApiError ? cause.message : "خطای ناشناخته رخ داد."
      );
    } finally {
      setLoading(false);
    }
  }

  const conversationOptions = conversations.map((conversation) => ({
    value: String(conversation.id),
    label: conversation.title,
  }));
  const activeConversation = conversations.find(
    (conversation) => conversation.id === activeId
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <SparklesIcon className="size-4 text-muted-foreground" />
          دستیار هوشمند بالینی
        </CardTitle>
        <CardDescription>
          گفتگوهای این بیمار ذخیره می‌شوند و پاسخ‌ها فقط بر اساس اطلاعات
          ثبت‌شدهٔ پرونده ساخته می‌شوند.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2">
          <Select
            items={conversationOptions}
            value={activeId == null ? null : String(activeId)}
            onValueChange={(value) => selectConversation(Number(value))}
            disabled={loadingConversations || conversations.length === 0}
          >
            <SelectTrigger
              className="h-9 w-full min-w-0"
              aria-label="انتخاب گفتگو"
            >
              <SelectValue
                placeholder={
                  loadingConversations
                    ? "در حال بارگذاری…"
                    : conversations.length === 0
                      ? "گفتگویی ثبت نشده است"
                      : "انتخاب گفتگو"
                }
              />
            </SelectTrigger>
            <SelectContent>
              {conversationOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            type="button"
            variant="outline"
            size="icon-sm"
            aria-label="گفتگوی جدید"
            title="گفتگوی جدید"
            onClick={handleNewConversation}
            disabled={loading}
          >
            <PlusIcon />
          </Button>
          {activeConversation ? (
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label="حذف گفتگو"
              title="حذف گفتگو"
              className="text-destructive hover:text-destructive"
              onClick={() => setDeleteOpen(true)}
              disabled={loading}
            >
              <Trash2Icon />
            </Button>
          ) : null}
        </div>

        <div
          ref={listRef}
          className="max-h-96 space-y-3 overflow-y-auto scroll-smooth"
        >
          {turns.length === 0 && !loading ? (
            <p className="rounded-lg bg-muted/50 px-4 py-6 text-center text-sm text-muted-foreground">
              {conversations.length === 0
                ? "با نوشتن اولین پرسش، گفتگوی جدیدی برای این بیمار ساخته می‌شود — مثلاً: «خلاصهٔ وضعیت بالینی بیمار چیست؟»"
                : "گفتگو خالی است — پرسش خود را بنویسید."}
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
                <>
                  <p className="whitespace-pre-wrap">{turn.content}</p>
                  {turn.evidence && turn.evidence.length > 0 ? (
                    <div className="mt-2 space-y-1.5 border-t pt-2">
                      <p className="text-[11px] font-medium text-muted-foreground">
                        شواهد بالینی
                      </p>
                      <ul className="space-y-1.5">
                        {turn.evidence.map((item) => (
                          <li
                            key={item.source_id}
                            className="flex flex-wrap items-center gap-1.5 text-xs leading-5"
                          >
                            {evidenceIcon(item.source_type)}
                            <span>{item.description}</span>
                            <span
                              className="text-muted-foreground/60"
                              dir="ltr"
                            >
                              {item.source_id}
                            </span>
                            {item.document_id ? (
                              <a
                                href={api.documentDownloadUrl(item.document_id)}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-0.5 font-medium text-primary underline-offset-2 hover:underline"
                              >
                                مشاهده سند اصلی
                                <ExternalLinkIcon className="size-3" />
                              </a>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </>
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

        <div className="flex items-center justify-between gap-2">
          <Button
            type="button"
            variant={safetyMode ? "secondary" : "outline"}
            size="sm"
            className="gap-1.5"
            aria-pressed={safetyMode}
            onClick={() => setSafetyMode((value) => !value)}
            disabled={loading}
          >
            <ShieldAlertIcon />
            بررسی ایمنی دارو
          </Button>
          {safetyMode ? (
            <p className="text-xs text-muted-foreground">
              حالت ایمنی دارو فعال است — نام داروی کاندید (و در صورت تمایل دوز
              و چند دارو) را همراه پرسش خود بنویسید.
            </p>
          ) : null}
        </div>

        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          <Textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={
              safetyMode
                ? "مثال: می‌خواهم وارفارین ۵ میلی‌گرم تجویز کنم؛ با داروهای فعلی بیمار تداخل دارد؟"
                : "پرسش خود را دربارهٔ بیمار بنویسید…"
            }
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

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="حذف گفتگو"
        description={`گفتگوی «${activeConversation?.title ?? "بدون عنوان"}» و همهٔ پیام‌های آن حذف می‌شود.`}
        confirmLabel="حذف قطعی"
        onConfirm={async () => {
          if (activeId == null) return;
          await api.deleteConversation(activeId);
          const remaining = conversations.filter(
            (conversation) => conversation.id !== activeId
          );
          setConversations(remaining);
          if (remaining.length > 0) {
            await selectConversation(remaining[0].id);
          } else {
            setActiveId(null);
            setTurns([]);
          }
        }}
      />
    </Card>
  );
}
