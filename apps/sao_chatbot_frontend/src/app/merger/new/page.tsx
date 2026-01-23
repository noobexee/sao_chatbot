"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { uploadDocument } from "@/libs/doc_manage/uploadDocument";
import { getDocuments, Doc } from "@/libs/doc_manage/getDocuments";
import { getDocStatus, DocStatusResponse } from "@/libs/doc_manage/getDocStatus";

function formatDDMMYYYY(value: string) {
  const digits = value.replace(/\D/g, "").slice(0, 8);
  const parts: string[] = [];
  if (digits.length >= 2) parts.push(digits.slice(0, 2));
  else if (digits.length > 0) parts.push(digits);
  if (digits.length >= 4) parts.push(digits.slice(2, 4));
  else if (digits.length > 2) parts.push(digits.slice(2));
  if (digits.length > 4) parts.push(digits.slice(4));
  return parts.join("-");
}

function ddmmyyyyToIso(value?: string): string | undefined {
  if (!value) return undefined;
  const [dd, mm, yyyy] = value.split("-");
  if (!dd || !mm || !yyyy) return undefined;
  if (dd.length !== 2 || mm.length !== 2 || yyyy.length !== 4) return undefined;
  return `${yyyy}-${mm}-${dd}`;
}

export default function NewDocumentPage() {
  const router = useRouter();

  const [file, setFile] = useState<File | null>(null);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [type, setType] = useState("");
  const [customType, setCustomType] = useState("");
  const [title, setTitle] = useState("");
  const [version, setVersion] = useState("");
  const [validFrom, setValidFrom] = useState("");
  const [validUntil, setValidUntil] = useState("");
  const [isFirstVersion, setIsFirstVersion] = useState(true);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [docId, setDocId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("queued");
  const [page, setPage] = useState<number | null>(null);
  const [totalPages, setTotalPages] = useState<number | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    getDocuments()
      .then(setDocs)
      .catch(() => setDocs([]));
  }, []);

  const types = useMemo(() => {
    return Array.from(new Set(docs.map((d) => d.type).filter(Boolean))).sort();
  }, [docs]);

  const resolvedType =
    type === "__new__" ? customType.trim() : type.trim();

  const onSubmit = async () => {
    if (!file || !resolvedType) {
      setError("กรุณาเลือกไฟล์ PDF และประเภทเอกสาร");
      return;
    }

    const announceIso = ddmmyyyyToIso(validFrom);
    const effectiveIso = ddmmyyyyToIso(validUntil);

    if (!announceIso) {
      setError("รูปแบบวันประกาศไม่ถูกต้อง (DD-MM-YYYY)");
      return;
    }
    if (!effectiveIso) {
      setError("รูปแบบวันมีผลบังคับใช้ไม่ถูกต้อง (DD-MM-YYYY)");
      return;
    }
    if (effectiveIso < announceIso) {
      setError("วันมีผลบังคับใช้ต้องไม่ก่อนวันประกาศ");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await uploadDocument({
        file,
        type: resolvedType,
        title: title || undefined,
        version: version || undefined,
        announce_date: announceIso,
        effective_date: effectiveIso,
        is_first_version: isFirstVersion,
      });

      setDocId(res.id);
      setStatusMessage("กำลังประมวลผลเอกสาร…");
    } catch (err: any) {
      setError(err.message || "อัปโหลดไม่สำเร็จ");
      setLoading(false);
    }
  };

  // 🔁 OCR status polling (restored)
  useEffect(() => {
    if (!docId) return;

    let timer: NodeJS.Timeout;

    const poll = async () => {
      try {
        const res: DocStatusResponse = await getDocStatus(docId);

        setStatus(res.status);
        setPage(res.current_page ?? null);
        setTotalPages(res.total_pages ?? null);
        setStatusMessage(res.message ?? "กำลังประมวลผล…");

        if (res.status === "done" || res.status === "merged") {
          router.replace(`/merger/${docId}/view`);
          return;
        }

        timer = setTimeout(poll, 3000);
      } catch {
        setError("ไม่สามารถตรวจสอบสถานะเอกสารได้");
      }
    };

    poll();
    return () => clearTimeout(timer);
  }, [docId, router]);

  return (
    <div className="h-full w-full p-6 max-w-3xl space-y-6">
      <h1 className="text-lg font-semibold text-gray-900">
        เพิ่มเอกสารใหม่
      </h1>

    {!docId && (
      <>
        <div className="space-y-1">
          <label className="text-sm font-medium">ไฟล์ PDF *</label>
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm"
          />
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium">ประเภทเอกสาร *</label>
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="w-full rounded-md border px-3 py-2 text-sm"
          >
            <option value="">— เลือกประเภท —</option>
            {types.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
            <option value="__new__">+ เพิ่มประเภทใหม่</option>
          </select>
        </div>

        {type === "__new__" && (
          <div className="space-y-1">
            <input
              value={customType}
              onChange={(e) => setCustomType(e.target.value)}
              placeholder="ประเภทเอกสารใหม่"
              className="w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>
        )}

        <div className="space-y-1">
          <label className="text-sm font-medium">ชื่อเอกสาร</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="ถ้าไม่กรอก ระบบจะ derive จาก PDF"
            className="w-full rounded-md border px-3 py-2 text-sm"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="text-sm font-medium">ฉบับที่</label>
            <input
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              disabled={isFirstVersion}
              className="w-full rounded-md border px-3 py-2 text-sm disabled:bg-gray-100"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium">
              วันประกาศ (DD-MM-YYYY) *
            </label>
            <input
              value={validFrom}
              onChange={(e) =>
                setValidFrom(formatDDMMYYYY(e.target.value))
              }
              placeholder="DD-MM-YYYY"
              className="w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium">
              วันมีผลบังคับใช้ (DD-MM-YYYY) *
            </label>
            <input
              value={validUntil}
              onChange={(e) =>
                setValidUntil(formatDDMMYYYY(e.target.value))
              }
              placeholder="DD-MM-YYYY"
              className="w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div className="flex items-start gap-2 pt-2">
          <input
            type="checkbox"
            checked={isFirstVersion}
            onChange={(e) => setIsFirstVersion(e.target.checked)}
            className="mt-1"
          />
          <label className="text-sm text-gray-700">
            เป็นฉบับแรกของเอกสารนี้, ไม่มีฉบับก่อนหน้า
          </label>
        </div>

        {error && (
          <p className="text-sm text-red-500 pt-1">
            {error}
          </p>
        )}

        <div className="pt-2">
          <button
            disabled={loading}
            onClick={onSubmit}
            className="rounded-md bg-blue-600 px-6 py-2 text-sm text-white disabled:opacity-50"
          >
            {loading ? "กำลังอัปโหลด…" : "อัปโหลดเอกสาร"}
          </button>
        </div>
      </>
    )}

      {docId && (
        <OCRProgress
          status={status}
          page={page}
          totalPages={totalPages}
          message={statusMessage}
        />
      )}
    </div>
  );
}

function OCRProgress({
  status,
  page,
  totalPages,
  message,
}: {
  status: string;
  page: number | null;
  totalPages: number | null;
  message?: string | null;
}) {
  const percent =
    page && totalPages ? Math.round((page / totalPages) * 100) : 0;

  return (
    <div className="space-y-2">
      <p className="text-sm text-gray-600">
        {message}
        {page && totalPages && <> • หน้า {page}/{totalPages}</>}
      </p>
      <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 transition-all"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
