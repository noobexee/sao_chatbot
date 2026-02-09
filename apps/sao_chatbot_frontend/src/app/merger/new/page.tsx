"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { uploadDocument } from "@/libs/doc_manage/uploadDocument";
import { getDocuments, DocumentMeta } from "@/libs/doc_manage/getDocuments";
import { getDocStatus, DocStatusResponse } from "@/libs/doc_manage/getDocStatus";
import OCRProgress from "@/components/OcrProgress";

/* ---------- helpers (unchanged) ---------- */
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

  const [mainFile, setMainFile] = useState<File | null>(null);
  const [optionalFiles, setOptionalFiles] = useState<File[]>([]);
  const [docs, setDocs] = useState<DocumentMeta[]>([]);

  const [type, setType] = useState("");
  const [customType, setCustomType] = useState("");
  const [title, setTitle] = useState("");
  const [validFrom, setValidFrom] = useState("");
  const [validUntil, setValidUntil] = useState("");
  const [isFirstVersion, setIsFirstVersion] = useState(true);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [previousDocId, setPreviousDocId] = useState<string>("");

  const [loading, setLoading] = useState(false);
  const [uploadDone, setUploadDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [docId, setDocId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("queued");
  const [page, setPage] = useState<number | null>(null);
  const [totalPages, setTotalPages] = useState<number | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  /* ---------- sidebar data (unchanged) ---------- */
  useEffect(() => {
    getDocuments().then(setDocs).catch(() => setDocs([]));
  }, []);

  const types = useMemo(() => {
    return Array.from(
      new Set(docs.map((d) => d.type).filter(Boolean))
    ).sort();
  }, [docs]);

  const resolvedType =
    type === "__new__" ? customType.trim() : type.trim();

  /* ---------- auto fill from previous doc ---------- */
  useEffect(() => {
    if (!previousDocId) return;

    const prev = docs.find((d) => d.id === previousDocId);
    if (!prev) return;

    setTitle(prev.title ?? "");
    setType(prev.type ?? "");
    setIsFirstVersion(false);
  }, [previousDocId, docs]);

  /* ---------- submit ---------- */
  const onSubmit = async () => {
    if (!mainFile || !resolvedType) {
      setError("กรุณาเลือกไฟล์เอกสารหลัก (PDF) และประเภทเอกสาร");
      return;
    }

    const announceIso = ddmmyyyyToIso(validFrom);
    const effectiveIso = ddmmyyyyToIso(validUntil);

    if (!announceIso || !effectiveIso) {
      setError("รูปแบบวันที่ไม่ถูกต้อง (DD-MM-YYYY)");
      return;
    }

    const prev = previousDocId
      ? docs.find((d) => d.id === previousDocId)
      : null;

    setLoading(true);
    setError(null);

    try {
      const res = await uploadDocument({
        doc_type: resolvedType,
        title: title || undefined,
        announce_date: announceIso,
        effective_date: effectiveIso,
        is_first_version: isFirstVersion,
        previous_doc_id: prev && !isFirstVersion ? prev.id : undefined,
        main_file: mainFile,
        related_files: optionalFiles.length ? optionalFiles : undefined,
      });

      window.dispatchEvent(new Event("documents:updated"));

      setDocId(res.id);
      setUploadDone(true);
      setStatus("queued");
      setStatusMessage("อัปโหลดสำเร็จ กำลังประมวลผลเอกสาร…");
    } catch (err: any) {
      setError(err?.message || "อัปโหลดไม่สำเร็จ");
      setLoading(false);
    }
  };

  /* ---------- OCR polling (unchanged) ---------- */
  useEffect(() => {
    if (!docId) return;

    let timer: NodeJS.Timeout;

    const poll = async () => {
      const res: DocStatusResponse = await getDocStatus(docId);

      setStatus(res.status);
      setPage(res.current_page ?? null);
      setTotalPages(res.total_pages ?? null);

      if (res.status === "done" || res.status === "merged") {
        window.dispatchEvent(new Event("documents:updated"));
        router.replace(`/merger/${docId}/view`);
        return;
      }

      timer = setTimeout(poll, 3000);
    };

    poll();
    return () => clearTimeout(timer);
  }, [docId, router]);

  return (
    <div className="h-full w-full p-6 max-w-3xl space-y-6">
      <h1 className="text-lg font-semibold text-gray-900">
        เพิ่มเอกสารใหม่
      </h1>

      {!uploadDone && (
        <>
          {/* ===== Has previous doc ===== */}
          <div className="space-y-2">
            <label className="text-sm font-medium">
              เอกสารนี้เคยมีในระบบหรือไม่ ?
            </label>
            <div className="flex gap-4 text-sm">
              <label className="flex items-center gap-1">
                <input
                  type="radio"
                  checked={!hasPrevious}
                  onChange={() => {
                    setHasPrevious(false);
                    setPreviousDocId("");
                    setIsFirstVersion(true);
                  }}
                />
                ไม่เคย
              </label>
              <label className="flex items-center gap-1">
                <input
                  type="radio"
                  checked={hasPrevious}
                  onChange={() => setHasPrevious(true)}
                />
                เคยมีแล้ว
              </label>
            </div>
          </div>

          {hasPrevious && (
            <div className="space-y-1">
              <label className="text-sm font-medium">
                เลือกเอกสารเดิม
              </label>
              <select
                value={previousDocId}
                onChange={(e) => setPreviousDocId(e.target.value)}
                className="w-full rounded-md border px-3 py-2 text-sm"
              >
                <option value="">— เลือกเอกสารเดิม —</option>
                {docs.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title} (v{d.version})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* ===== Main file ===== */}
          <div className="space-y-1">
            <label className="text-sm font-medium">
              ไฟล์เอกสารหลัก (PDF เท่านั้น) *
            </label>
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) =>
                setMainFile(e.target.files?.[0] ?? null)
              }
              className="block w-full text-sm"
            />
          </div>

          {/* ===== Optional files ===== */}
          <div className="space-y-1">
            <label className="text-sm font-medium">
              ไฟล์ที่เกี่ยวข้อง (ถ้ามี)
            </label>
            <input
              type="file"
              multiple
              onChange={(e) =>
                setOptionalFiles(Array.from(e.target.files ?? []))
              }
              className="block w-full text-sm"
            />
          </div>

          {/* ===== Type ===== */}
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
            <input
              value={customType}
              onChange={(e) => setCustomType(e.target.value)}
              placeholder="ประเภทเอกสารใหม่"
              className="w-full rounded-md border px-3 py-2 text-sm"
            />
          )}

          {/* ===== Title ===== */}
          <div className="space-y-1">
            <label className="text-sm font-medium">ชื่อเอกสาร</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="ถ้าไม่กรอก ระบบจะ derive จาก PDF"
              className="w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>

          {/* ===== Dates ===== */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

          {error && (
            <p className="text-sm text-red-500 pt-1">{error}</p>
          )}

          <button
            disabled={loading || !mainFile || !resolvedType}
            onClick={onSubmit}
            className="rounded-md bg-blue-600 px-6 py-2 text-sm text-white disabled:opacity-50"
          >
            {loading ? "กำลังอัปโหลด…" : "อัปโหลดเอกสาร"}
          </button>
        </>
      )}

      {uploadDone && (
        <div className="rounded-md border border-green-200 bg-green-50 p-4">
          <p className="text-sm font-medium text-green-800">
            ✅ อัปโหลดเอกสารเรียบร้อยแล้ว
          </p>
          <p className="text-sm text-green-700">
            ระบบกำลังประมวลผลเอกสาร กรุณารอสักครู่…
          </p>
        </div>
      )}

      {docId && (
        <OCRProgress
          status={status}
          page={page}
          totalPages={totalPages}
          message= "กำลังประมวลผล…"
        />
      )}
    </div>
  );
}