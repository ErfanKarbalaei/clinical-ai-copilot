"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import {
  CircleStopIcon,
  FileTextIcon,
  MicIcon,
  PlayIcon,
  RotateCcwIcon,
  Trash2Icon,
  UploadIcon,
} from "lucide-react";

import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import {
  conversationTypeOptions,
  formatDuration,
} from "@/lib/format";
import type { ConversationType, VoiceNote } from "@/lib/types";

/** Pick the best audio mime type this browser can record. */
function supportedMimeType(): string {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
  ];
  for (const candidate of candidates) {
    if (
      typeof MediaRecorder !== "undefined" &&
      MediaRecorder.isTypeSupported(candidate)
    ) {
      return candidate;
    }
  }
  return "";
}

/** Record-or-upload dialog → POST /patients/{id}/voice-notes. */
export function AddVoiceNoteButton({ patientId }: { patientId: number }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"record" | "file">("record");
  const [title, setTitle] = useState("");
  const [conversationType, setConversationType] =
    useState<ConversationType>("physician_note");
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const recordedRef = useRef<{ file: File; seconds: number } | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) return;
    // reset whenever the dialog closes
    stopTimer();
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
    recorderRef.current = null;
    recordedRef.current = null;
    setRecording(false);
    setSeconds(0);
    setFile(null);
    setMode("record");
    setTitle("");
    setConversationType("physician_note");
    setError(null);
    setSubmitting(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  function stopTimer() {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  async function startRecording() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = supportedMimeType();
      const recorder = new MediaRecorder(
        stream,
        mimeType ? { mimeType } : undefined
      );
      chunksRef.current = [];
      recordedRef.current = null;
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const extension = mimeType.includes("mp4") ? "m4a" : "webm";
        const blob = new Blob(chunksRef.current, { type: mimeType || "audio/webm" });
        recordedRef.current = {
          file: new File([blob], `recording.${extension}`, {
            type: blob.type || "audio/webm",
          }),
          seconds,
        };
      };
      recorder.start();
      recorderRef.current = recorder;
      setSeconds(0);
      setRecording(true);
      timerRef.current = setInterval(() => setSeconds((value) => value + 1), 1000);
    } catch {
      setError("دسترسی به میکروفون ممکن نشد — می‌توانید از حالت «انتخاب فایل» استفاده کنید.");
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
    stopTimer();
    setRecording(false);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const source =
      mode === "record" ? recordedRef.current : file ? { file, seconds: 0 } : null;
    if (!source?.file) {
      setError(mode === "record" ? "اول ضبط کنید." : "انتخاب فایل صوتی الزامی است.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.uploadVoiceNote(patientId, {
        file: source.file,
        title: title.trim() || undefined,
        conversationType,
        durationSeconds: mode === "record" ? source.seconds : undefined,
      });
      setOpen(false);
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError ? cause.message : "بارگذاری با خطا مواجه شد."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Button
        variant="outline"
        size="icon-sm"
        aria-label="ثبت یادداشت صوتی"
        onClick={() => setOpen(true)}
      >
        <MicIcon />
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>یادداشت صوتی جدید</DialogTitle>
            <DialogDescription>
              فایل صوتی اصلی دست‌نخورده ذخیره می‌شود؛ تبدیل گفتار فارسی به متن
              بلافاصله پس از ثبت انجام می‌شود.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4" id="voice-note-form">
            <div className="flex rounded-lg border p-1">
              <Button
                type="button"
                variant={mode === "record" ? "secondary" : "ghost"}
                size="sm"
                className="flex-1"
                onClick={() => setMode("record")}
              >
                <MicIcon />
                ضبط صدا
              </Button>
              <Button
                type="button"
                variant={mode === "file" ? "secondary" : "ghost"}
                size="sm"
                className="flex-1"
                onClick={() => setMode("file")}
              >
                <UploadIcon />
                انتخاب فایل
              </Button>
            </div>

            {mode === "record" ? (
              <div className="flex flex-col items-center gap-3 rounded-lg bg-muted/50 py-6">
                <Button
                  type="button"
                  size="lg"
                  variant={recording ? "destructive" : "default"}
                  onClick={recording ? stopRecording : startRecording}
                >
                  {recording ? <CircleStopIcon /> : <MicIcon />}
                  {recording ? `پایان ضبط (${formatDuration(seconds)})` : "شروع ضبط"}
                </Button>
                {recordedRef.current && !recording ? (
                  <p className="text-xs text-muted-foreground" dir="ltr">
                    ✓ {recordedRef.current.file.name} —{" "}
                    {formatDuration(recordedRef.current.seconds)}
                  </p>
                ) : null}
              </div>
            ) : (
              <div className="space-y-2">
                <Label htmlFor="voice_file">فایل صوتی *</Label>
                <Input
                  id="voice_file"
                  ref={fileInputRef}
                  type="file"
                  accept="audio/*,.webm,.ogg,.mp3,.m4a,.wav"
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                  required
                />
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="voice_title">عنوان</Label>
              <Input
                id="voice_title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={300}
                placeholder="مثال: یادداشت ویزیت امروز"
              />
            </div>
            <div className="space-y-2">
              <Label>نوع گفتگو</Label>
              <Select
                items={conversationTypeOptions}
                value={conversationType}
                onValueChange={(value) =>
                  setConversationType(value as ConversationType)
                }
              >
                <SelectTrigger className="w-full" aria-label="نوع گفتگو">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {conversationTypeOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label} — {option.description}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {error ? <p className="text-sm text-destructive">{error}</p> : null}
          </form>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              انصراف
            </Button>
            <Button type="submit" form="voice-note-form" disabled={submitting}>
              {submitting ? "در حال ارسال…" : "ثبت و تبدیل به متن"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

/** Review/edit the raw transcript → save as a clinical note. */
function CreateNoteFromVoiceDialog({
  voiceNote,
  open,
  onOpenChange,
}: {
  voiceNote: VoiceNote;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setTitle(voiceNote.title ?? "یادداشت صوتی");
    setContent(voiceNote.transcript ?? "");
    setError(null);
    setSubmitting(false);
  }, [open, voiceNote]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.createNoteFromVoiceNote(voiceNote.id, {
        title: title.trim(),
        content,
      });
      onOpenChange(false);
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError ? cause.message : "ثبت یادداشت با خطا مواجه شد."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>تبدیل رونوشت به یادداشت بالینی</DialogTitle>
          <DialogDescription>
            متن خام را بازبینی و اصلاح کنید؛ نسخهٔ نهایی با پیوند به فایل صوتی
            اصلی در پرونده ثبت می‌شود.
          </DialogDescription>
        </DialogHeader>
        <form id="voice-note-form" onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="note_title">عنوان یادداشت *</Label>
            <Input
              id="note_title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              required
              maxLength={300}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="note_content">متن یادداشت (رونوشت خام) *</Label>
            <Textarea
              id="note_content"
              value={content}
              onChange={(event) => setContent(event.target.value)}
              required
              rows={8}
            />
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </form>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            انصراف
          </Button>
          <Button type="submit" form="voice-note-form" disabled={submitting}>
            {submitting ? "در حال ذخیره…" : "ثبت در پرونده"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** View the raw transcript (read-only). */
export function ViewTranscriptButton({ voiceNote }: { voiceNote: VoiceNote }) {
  const [open, setOpen] = useState(false);
  if (!voiceNote.transcript) return null;
  return (
    <>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="مشاهدهٔ رونوشت خام"
        title="رونوشت خام"
        onClick={() => setOpen(true)}
      >
        <FileTextIcon />
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>رونوشت خام — {voiceNote.title ?? "بدون عنوان"}</DialogTitle>
            <DialogDescription>
              خروجی تبدیل گفتار به متن، بدون هیچ ویرایشی. فایل صوتی اصلی معتبرترین
              منبع است.
            </DialogDescription>
          </DialogHeader>
          <pre className="max-h-80 overflow-auto rounded-lg bg-muted/50 p-4 text-sm whitespace-pre-wrap">
            {voiceNote.transcript}
          </pre>
        </DialogContent>
      </Dialog>
    </>
  );
}

/** Per-row actions: audio download/play, note-from-transcript, retry, delete. */
export function VoiceNoteRowActions({ voiceNote }: { voiceNote: VoiceNote }) {
  const router = useRouter();
  const [noteOpen, setNoteOpen] = useState(false);
  const [retryOpen, setRetryOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  return (
    <div className="flex items-center gap-1">
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="پخش/دانلود فایل صوتی"
        title="پخش/دانلود فایل صوتی"
        render={
          <a
            href={api.voiceNoteDownloadUrl(voiceNote.id)}
            target="_blank"
            rel="noreferrer"
          />
        }
      >
        <PlayIcon />
      </Button>
      {voiceNote.transcription_status === "completed" ? (
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="ثبت یادداشت از رونوشت"
          title="بازبینی و ثبت به‌عنوان یادداشت بالینی"
          onClick={() => setNoteOpen(true)}
        >
          <FileTextIcon />
        </Button>
      ) : null}
      {voiceNote.transcription_status === "failed" ? (
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="تبدیل مجدد"
          title="تلاش دوباره برای تبدیل به متن"
          onClick={() => setRetryOpen(true)}
        >
          <RotateCcwIcon />
        </Button>
      ) : null}
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="حذف"
        className="text-destructive hover:text-destructive"
        onClick={() => setDeleteOpen(true)}
      >
        <Trash2Icon />
      </Button>

      {voiceNote.transcription_status === "completed" ? (
        <CreateNoteFromVoiceDialog
          voiceNote={voiceNote}
          open={noteOpen}
          onOpenChange={setNoteOpen}
        />
      ) : null}
      <ConfirmDialog
        open={retryOpen}
        onOpenChange={setRetryOpen}
        title="تبدیل مجدد به متن"
        description="تبدیل گفتار به متن دوباره اجرا می‌شود (مثلاً پس از پیکربندی کلید سرویس)."
        confirmLabel="تبدیل مجدد"
        onConfirm={async () => {
          await api.retranscribeVoiceNote(voiceNote.id);
          router.refresh();
        }}
      />
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="حذف یادداشت صوتی"
        description={`فایل صوتی «${voiceNote.title ?? "بدون عنوان"}» حذف می‌شود؛ یادداشت‌های بالینی گرفته‌شده از آن باقی می‌مانند.`}
        confirmLabel="حذف قطعی"
        onConfirm={async () => {
          await api.deleteVoiceNote(voiceNote.id);
          router.refresh();
        }}
      />
    </div>
  );
}
