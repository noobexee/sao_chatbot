"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { uploadDocument } from "@/libs/doc_manage/uploadDocument";
import { getDocuments, Doc } from "@/libs/doc_manage/getDocuments";
import { getDocStatus } from "@/libs/doc_manage/getDocStatus";

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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [docId, setDocId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    getDocuments()
      .then(setDocs)
      .catch(() => setDocs([]));
  }, []);

  const types = useMemo(() => {
    return Array.from(
      new Set(docs.map((d) => d.type).filter(Boolean))
    ).sort();
  }, [docs]);

  const resolvedType =
    type === "__new__" ? customType.trim() : type.trim();
  
  const onSubmit = async () => {
    if (!file || !resolvedType) {
      setError("กรุณาเลือกไฟล์ PDF และประเภทเอกสาร");
      return;
    }
    setLoading(true);
    setError(null);
    if (validFrom && !ddmmyyyyToIso(validFrom)) {
      setError("รูปแบบวันที่ใช้ตั้งแต่ไม่ถูกต้อง");
      return;
    }
    if (validUntil && !ddmmyyyyToIso(validUntil)) {
      setError("รูปแบบวันที่ใช้ถึงไม่ถูกต้อง");
      return;
    }
    try {
      const res = await uploadDocument({
        file,
        type: resolvedType,
        title: title || undefined,
        version: version || undefined,
        valid_from: ddmmyyyyToIso(validFrom),
        valid_until: ddmmyyyyToIso(validUntil),
      });
      setDocId(res.id);
      setStatusMessage("กำลังประมวลผลเอกสาร…");
    } catch (err: any) {
      setError(err.message || "อัปโหลดไม่สำเร็จ");
      setLoading(false);
    }
  };
  useEffect(() => {
    if (!docId) return;
    let timer: NodeJS.Timeout;
    const poll = async () => {
      try {
        const res = await getDocStatus(docId);
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
                <option key={t} value={t}>{t}</option>
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
          <div className="space-y-1">
            <label className="text-sm font-medium">ชื่อเอกสาร</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="ถ้าไม่กรอก ระบบจะ derive จาก PDF"
              className="w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">ฉบับที่</label>
              <input
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                className="w-full rounded-md border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-sm font-medium">
                ใช้ตั้งแต่ (DD-MM-YYYY)
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
            <div>
              <label className="text-sm font-medium">
                ใช้ถึง (DD-MM-YYYY)
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
          {error && <p className="text-sm text-red-500">{error}</p>}
          <button
            disabled={loading}
            onClick={onSubmit}
            className="rounded-md bg-blue-600 px-6 py-2 text-sm text-white disabled:opacity-50"
          >
            {loading ? "กำลังอัปโหลด…" : "อัปโหลดเอกสาร"}
          </button>
        </>
      )}
      {docId && (
        <div className="space-y-2">
          <p className="text-sm text-gray-600">{statusMessage}</p>
          <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
            <div className="h-full w-1/2 bg-blue-500 animate-pulse" />
          </div>
        </div>
      )}
    </div>
  );
}
