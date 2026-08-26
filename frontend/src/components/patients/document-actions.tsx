"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import {
  FileUpIcon,
  PencilIcon,
  RotateCcwIcon,
  Trash2Icon,
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
import { ApiError, api } from "@/lib/api";
import { documentTypeOptions } from "@/lib/format";
import type { Document, DocumentType } from "@/lib/types";

const FORM_ID = "document-upload-form";

/** «بارگذاری سند» — multipart upload dialog. */
export function AddDocumentButton({ patientId }: { patientId: number }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [docType, setDocType] = useState<DocumentType>("other");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setFile(null);
    setTitle("");
    setDocType("other");
    setError(null);
    setSubmitting(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, [open]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) {
      setError("انتخاب فایل الزامی است.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.uploadDocument(patientId, {
        file,
        title: title.trim() || undefined,
        docType,
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
        aria-label="بارگذاری سند"
        onClick={() => setOpen(true)}
      >
        <FileUpIcon />
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>بارگذاری سند جدید</DialogTitle>
            <DialogDescription>
              فایل اصلی دست‌نخورده ذخیره می‌شود؛ استخراج متن (PDF/OCR) بلافاصله
              پس از بارگذاری انجام می‌شود. PDF، تصویر یا متن — حداکثر ۲۰ مگابایت.
            </DialogDescription>
          </DialogHeader>

          <form id={FORM_ID} onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="document_file">فایل *</Label>
              <Input
                id="document_file"
                ref={fileInputRef}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.webp,.txt"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                required
              />
              {file ? (
                <p className="text-xs text-muted-foreground" dir="ltr">
                  {file.name} — {Math.ceil(file.size / 1024)} KB
                </p>
              ) : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="document_title">عنوان</Label>
              <Input
                id="document_title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={300}
                placeholder="پیش‌فرض: نام فایل"
              />
            </div>
            <div className="space-y-2">
              <Label>نوع سند</Label>
              <Select
                items={documentTypeOptions}
                value={docType}
                onValueChange={(value) => setDocType(value as DocumentType)}
              >
                <SelectTrigger className="w-full" aria-label="نوع سند">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {documentTypeOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {error ? (
              <p className="text-sm text-destructive">{error}</p>
            ) : null}
          </form>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={submitting}
            >
              انصراف
            </Button>
            <Button type="submit" form={FORM_ID} disabled={submitting}>
              {submitting ? "در حال بارگذاری…" : "بارگذاری"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

/** View the extracted (deterministic) text of a processed document. */
export function ViewExtractedTextButton({ document }: { document: Document }) {
  const [open, setOpen] = useState(false);
  if (document.extraction_status !== "completed" || !document.extracted_text) {
    return null;
  }
  return (
    <>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="مشاهدهٔ متن استخراج‌شده"
        title="متن استخراج‌شده"
        onClick={() => setOpen(true)}
      >
        <PencilIcon />
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>متن استخراج‌شده — {document.title}</DialogTitle>
            <DialogDescription>
              متن به‌صورت خودکار و قطعی (بدون هوش مصنوعی) از فایل اصلی
              استخراج شده است؛ فایل اصلی معتبرترین منبع است.
            </DialogDescription>
          </DialogHeader>
          <pre className="max-h-80 overflow-auto rounded-lg bg-muted/50 p-4 text-sm whitespace-pre-wrap">
            {document.extracted_text}
          </pre>
        </DialogContent>
      </Dialog>
    </>
  );
}

/** Per-row actions: re-extract (when failed), delete. */
export function DocumentRowActions({ document }: { document: Document }) {
  const router = useRouter();
  const [reextractOpen, setReextractOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  return (
    <div className="flex items-center gap-1">
      {document.extraction_status === "failed" ? (
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="پردازش مجدد"
          title="تلاش دوباره برای استخراج متن"
          onClick={() => setReextractOpen(true)}
        >
          <RotateCcwIcon />
        </Button>
      ) : null}
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="حذف سند"
        className="text-destructive hover:text-destructive"
        onClick={() => setDeleteOpen(true)}
      >
        <Trash2Icon />
      </Button>

      <ConfirmDialog
        open={reextractOpen}
        onOpenChange={setReextractOpen}
        title="پردازش مجدد سند"
        description="استخراج متن دوباره اجرا می‌شود (مثلاً پس از نصب موتور OCR)."
        confirmLabel="پردازش مجدد"
        onConfirm={async () => {
          await api.reextractDocument(document.id);
          router.refresh();
        }}
      />
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="حذف سند"
        description={`فایل اصلی «${document.title}» به‌همراه فرادادهٔ آن حذف می‌شود. این عمل بازگشت‌پذیر نیست.`}
        confirmLabel="حذف قطعی"
        onConfirm={async () => {
          await api.deleteDocument(document.id);
          router.refresh();
        }}
      />
    </div>
  );
}
