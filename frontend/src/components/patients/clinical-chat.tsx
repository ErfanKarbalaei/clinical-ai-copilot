"use client";

import { useEffect, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import {
  ActivityIcon,
  CheckIcon,
  ClipboardListIcon,
  CopyIcon,
  FlaskConicalIcon,
  PillIcon,
  PlusIcon,
  SendIcon,
  ShieldCheckIcon,
  SparklesIcon,
  Trash2Icon,
  WrenchIcon,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { AnswerText } from "@/components/patients/copilot/answer-text";
import { EvidenceList } from "@/components/patients/copilot/evidence-list";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { ApiError, api } from "@/lib/api";
import { formatTime } from "@/lib/format";
import type {
  AIProviderInfo,
  ConversationSummary,
  EvidenceItem,
} from "@/lib/types";

const MAX_QUESTION_LENGTH = 2000;

/** One rendered chat turn — assistant turns may carry validated evidence. */
interface RenderedTurn {
  role: "user" | "assistant";
  content: string;
  evidence?: EvidenceItem[];
  toolsUsed?: { name: string; label: string }[];
  createdAt?: string | null;
}

/** Clinically useful starter questions (Phase 1 design empty state). */
const SUGGESTIONS: { text: string; icon: LucideIcon }[] = [
  { text: "خلاصهٔ وضعیت بالینی بیمار چیست؟", icon: ClipboardListIcon },
  { text: "داروهای فعلی و نکات مهم آن‌ها را مرور کن", icon: PillIcon },
  { text: "آخرین آزمایش‌های غیرطبیعی کدام‌اند؟", icon: FlaskConicalIcon },
  {
    text: "در وضعیت اخیر بیمار چه تغییرات مهمی دیده می‌شود؟",
    icon: ActivityIcon,
  },
];

function ModeChip({
  active,
  disabled,
  icon: Icon,
  label,
  onClick,
}: {
  active: boolean;
  disabled?: boolean;
  icon: LucideIcon;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "inline-flex h-7 items-center gap-1.5 rounded-lg border px-2.5 text-xs transition-colors disabled:opacity-50",
        active
          ? "border-brand-border bg-brand-soft font-medium text-brand"
          : "border-border bg-card text-muted-foreground hover:bg-surface-2"
      )}
    >
      <Icon className="size-3.5" />
      {label}
    </button>
  );
}

/**
 * AI clinical copilot panel (Phase 1 design) — a full-height supporting
 * panel beside the patient record. All conversation, provider-selection,
 * medication-safety and agent-mode behavior is unchanged; only the
 * presentation was redesigned.
 */
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
  // MCP/agent spike: stateless path — answers are not saved to conversations
  const [agentMode, setAgentMode] = useState(false);
  // runtime provider/model selection (ids only — persisted in localStorage)
  const [aiProviders, setAiProviders] = useState<AIProviderInfo[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
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
              createdAt: message.created_at,
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
    // load the provider/model catalog (ids only — never keys); failure is
    // non-fatal: the chat simply falls back to the server-side default
    let cancelled = false;
    (async () => {
      try {
        const response = await api.getAIProviders();
        if (cancelled || response.providers.length === 0) return;
        setAiProviders(response.providers);
        const storedProvider = window.localStorage.getItem("clinical_ai_provider");
        const storedModel = window.localStorage.getItem("clinical_ai_model");
        const provider = response.providers.find(
          (candidate) => candidate.id === storedProvider
        );
        if (provider) {
          setSelectedProvider(provider.id);
          const model = provider.models.find((m) => m.id === storedModel);
          setSelectedModel(model ? model.id : provider.models[0]?.id ?? null);
        }
      } catch {
        // catalog unavailable → env-default provider keeps working
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    // keep the newest message in view
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [turns, loading]);

  // one compact "provider · model" selector (a configuration detail, not a
  // primary task — Phase 1 design keeps it as a small chip near the input)
  const modelOptions = aiProviders.flatMap((provider) =>
    provider.models.map((model) => ({
      value: `${provider.id}::${model.id}`,
      label: `${provider.name} · ${model.name}`,
    }))
  );
  const selectedModelValue =
    selectedProvider && selectedModel
      ? `${selectedProvider}::${selectedModel}`
      : null;

  function handleModelValueChange(value: string | null) {
    if (!value) return;
    const separator = value.indexOf("::");
    const providerId = value.slice(0, separator);
    const modelId = value.slice(separator + 2);
    setSelectedProvider(providerId);
    setSelectedModel(modelId);
    window.localStorage.setItem("clinical_ai_provider", providerId);
    window.localStorage.setItem("clinical_ai_model", modelId);
  }

  const conversationOptions = conversations.map((conversation) => ({
    value: String(conversation.id),
    label: conversation.title,
  }));
  const activeConversation = conversations.find(
    (conversation) => conversation.id === activeId
  );

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
          createdAt: message.created_at,
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

  // Enter sends (Shift+Enter = newline) — matches the hint under the input
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      if (question.trim() && !loading) {
        handleSubmit(event);
      }
    }
  }

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setError(null);
    setTurns((previous) => [
      ...previous,
      { role: "user", content: trimmed, createdAt: new Date().toISOString() },
    ]);
    setLoading(true);

    try {
      // continue the active conversation (create one implicitly if none)
      let conversationId = activeId;
      if (conversationId == null) {
        const conversation = await api.createConversation(patientId);
        conversationId = conversation.id;
        setActiveId(conversation.id);
        setConversations((previous) => [conversation, ...previous]);
      }

      if (agentMode) {
        // stateless agent path (MCP spike) — no conversation persistence
        const response = await api.agentChat(patientId, trimmed);
        setTurns((previous) => [
          ...previous,
          {
            role: "assistant",
            content: response.answer,
            toolsUsed: response.tools_used,
            createdAt: response.generated_at,
          },
        ]);
        return;
      }

      const response = await api.sendConversationMessage(conversationId, {
        content: trimmed,
        medication_safety: safetyMode,
        provider: selectedProvider ?? undefined,
        model: selectedModel ?? undefined,
      });

      setTurns((previous) => [
        ...previous,
        {
          role: "assistant",
          content: response.assistant_message.content,
          evidence: response.assistant_message.evidence ?? undefined,
          createdAt: response.assistant_message.created_at,
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

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading) return;
    setQuestion("");
    void send(trimmed);
  }

  async function handleCopy(index: number, content: string) {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedIndex(index);
      window.setTimeout(() => setCopiedIndex(null), 2000);
    } catch {
      // clipboard unavailable (e.g. insecure context) — silently ignore
    }
  }

  return (
    <section
      aria-label="دستیار بالینی"
      className="flex h-[75svh] min-h-0 flex-col overflow-hidden bg-surface-2 xl:sticky xl:top-4 xl:h-[calc(100svh-2.5rem)] xl:border-s"
    >
      {/* panel header — grounding statement */}
      <header className="flex shrink-0 items-center justify-end gap-2 border-b bg-card px-4 py-2.5">
        <div className="text-end">
          <h2 className="text-[15px] leading-5 font-semibold">دستیار بالینی</h2>
          <p className="text-xs text-faint">
            پاسخ‌ها بر اساس پروندهٔ همین بیمار هستند
          </p>
        </div>
        <SparklesIcon className="size-4 shrink-0 text-brand" />
      </header>

      {/* conversations — preserved selector, kept compact */}
      <div className="flex shrink-0 items-center gap-1.5 border-b bg-card px-3 py-1.5">
        <div className="min-w-0 flex-1">
          <Select
            items={conversationOptions}
            value={activeId == null ? null : String(activeId)}
            onValueChange={(value) => selectConversation(Number(value))}
            disabled={loadingConversations || conversations.length === 0}
          >
            <SelectTrigger
              className="h-7 w-full min-w-0 text-xs"
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
        </div>
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

      {/* messages / empty state */}
      <div
        ref={listRef}
        className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-3.5 py-4"
      >
        {turns.length === 0 && !loading ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-4 py-4 text-center">
            <span className="flex size-11 items-center justify-center rounded-full bg-brand-soft">
              <SparklesIcon className="size-5 text-brand" />
            </span>
            <div className="space-y-1.5">
              <p className="text-[15px] font-semibold">
                دربارهٔ وضعیت این بیمار از من بپرسید.
              </p>
              <p className="mx-auto max-w-[340px] text-xs leading-6 text-muted-foreground">
                پاسخ‌ها از اطلاعات ثبت‌شدهٔ پرونده ساخته می‌شوند و همراه با ذکر
                منبع نمایش داده می‌شوند.
              </p>
            </div>
            <div className="w-full space-y-2">
              {SUGGESTIONS.map(({ text, icon: Icon }) => (
                <button
                  key={text}
                  type="button"
                  onClick={() => void send(text)}
                  disabled={loading}
                  className="flex w-full items-center gap-2.5 rounded-lg border bg-card px-3.5 py-2.5 text-start text-[13px] font-medium transition-colors hover:border-brand-border hover:bg-brand-soft disabled:opacity-50"
                >
                  <Icon className="size-3.5 shrink-0 text-faint" />
                  {text}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {turns.map((turn, index) =>
          turn.role === "user" ? (
            <div
              key={index}
              className="ms-auto w-fit max-w-[85%] rounded-lg border bg-card px-3 py-2"
            >
              <p className="text-[13px] leading-6 font-medium">{turn.content}</p>
              {turn.createdAt ? (
                <p className="mt-0.5 text-[11px] text-faint">
                  {formatTime(turn.createdAt)}
                </p>
              ) : null}
            </div>
          ) : (
            <div
              key={index}
              className="w-full rounded-xl border border-brand-border bg-brand-soft p-3.5"
            >
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="flex items-center gap-1 text-[11px] font-semibold text-muted-foreground">
                  <SparklesIcon className="size-3 text-brand" />
                  پاسخ دستیار بالینی
                </span>
                <span className="flex items-center gap-1.5">
                  {turn.createdAt ? (
                    <span className="text-[11px] text-faint">
                      {formatTime(turn.createdAt)}
                    </span>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => void handleCopy(index, turn.content)}
                    aria-label="کپی پاسخ"
                    title="کپی پاسخ"
                    className="text-faint transition-colors hover:text-brand"
                  >
                    {copiedIndex === index ? (
                      <CheckIcon className="size-3.5 text-success" />
                    ) : (
                      <CopyIcon className="size-3.5" />
                    )}
                  </button>
                </span>
              </div>
              <AnswerText content={turn.content} />
              {turn.toolsUsed && turn.toolsUsed.length > 0 ? (
                <p className="mt-2 text-[11px] leading-5 text-faint">
                  ابزارهای استفاده‌شده:{" "}
                  {turn.toolsUsed.map((tool) => tool.label).join("، ")}
                </p>
              ) : null}
              {turn.evidence && turn.evidence.length > 0 ? (
                <div className="mt-3">
                  <EvidenceList
                    patientId={patientId}
                    evidence={turn.evidence}
                  />
                </div>
              ) : null}
            </div>
          )
        )}

        {loading ? (
          <div
            className="w-full rounded-xl border border-brand-border bg-brand-soft p-3.5"
            aria-live="polite"
          >
            <p className="flex items-center gap-2 text-[13px] font-medium">
              <span className="relative flex size-2 shrink-0">
                <span className="absolute inline-flex size-2 animate-ping rounded-full bg-brand opacity-60" />
                <span className="relative inline-flex size-2 rounded-full bg-brand" />
              </span>
              در حال بررسی پرونده و پردازش پاسخ…
            </p>
            <div className="mt-3 space-y-2">
              <div className="h-2.5 w-full animate-pulse rounded-full bg-card" />
              <div className="h-2.5 w-4/5 animate-pulse rounded-full bg-card" />
              <div className="h-2.5 w-3/5 animate-pulse rounded-full bg-card" />
            </div>
          </div>
        ) : null}

        {error ? <p className="text-xs text-critical">{error}</p> : null}
      </div>

      {/* controls + composer */}
      <div className="shrink-0 space-y-2 border-t bg-card px-3.5 pb-3 pt-2.5">
        <div className="flex items-center justify-between gap-2">
          {/* modes — right in RTL */}
          <div className="flex items-center gap-1.5">
            <ModeChip
              active={safetyMode}
              disabled={loading}
              icon={ShieldCheckIcon}
              label="بررسی ایمنی دارو"
              onClick={() => setSafetyMode((value) => !value)}
            />
            <ModeChip
              active={agentMode}
              disabled={loading}
              icon={WrenchIcon}
              label="حالت ابزار"
              onClick={() => setAgentMode((value) => !value)}
            />
          </div>
          {/* model — a configuration chip, not a primary task */}
          {modelOptions.length > 0 ? (
            <Select
              items={modelOptions}
              value={selectedModelValue}
              onValueChange={handleModelValueChange}
            >
              <SelectTrigger
                size="sm"
                className="h-6 gap-1 rounded-md border-transparent bg-surface-2 px-2 font-mono text-[11px] text-muted-foreground"
                aria-label="انتخاب مدل هوش مصنوعی"
              >
                <SelectValue placeholder="مدل پیش‌فرض" />
              </SelectTrigger>
              <SelectContent>
                {modelOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : null}
        </div>

        {agentMode ? (
          <p className="text-[11px] leading-5 text-faint">
            حالت ابزار فعال است — پاسخ‌ها با ابزارهای فقط-خواندنی از پروندهٔ
            واقعی ساخته می‌شوند و در گفتگو ذخیره نمی‌شوند.
          </p>
        ) : safetyMode ? (
          <p className="text-[11px] leading-5 text-faint">
            حالت ایمنی دارو فعال است — نام داروی کاندید (و در صورت تمایل دوز
            و چند دارو) را همراه پرسش خود بنویسید.
          </p>
        ) : null}

        <form onSubmit={handleSubmit} className="space-y-1.5">
          <div className="flex items-end gap-2">
            <Textarea
              value={question}
              onKeyDown={handleKeyDown}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="سؤال خود را درباره این بیمار بنویسید…"
              rows={2}
              maxLength={MAX_QUESTION_LENGTH}
              disabled={loading}
              className="min-h-11 flex-1 resize-none border-transparent bg-surface-2 text-[13px]"
            />
            <Button
              type="submit"
              size="lg"
              className="size-9 shrink-0"
              disabled={loading || question.trim() === ""}
              aria-label="ارسال پرسش"
            >
              <SendIcon className="rtl:-scale-x-100" />
            </Button>
          </div>
          <div className="flex items-center justify-between gap-2 px-1">
            <p className="text-[11px] leading-5 text-faint">
              پاسخ‌ها ابزار کمک تصمیم‌گیری‌اند؛ مسئولیت نهایی با پزشک است.
            </p>
            <p className="shrink-0 text-[11px] text-faint">
              Enter ارسال · Shift+Enter خط جدید
            </p>
          </div>
        </form>
      </div>

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
    </section>
  );
}
