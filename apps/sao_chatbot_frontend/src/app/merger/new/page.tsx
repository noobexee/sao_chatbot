"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { uploadDocument } from "@/libs/doc_manage/uploadDocument";
import { getDocuments, Doc } from "@/libs/doc_manage/getDocuments";

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

  useEffect(() => {
    getDocuments()
      .then(setDocs)
      .catch(() => setDocs([]));
  }, []);

  const types = useMemo(() => {
    return Array.from(
      new Set(
        docs
          .map((d) => d.type)
          .filter(Boolean)
      )
    ).sort();
  }, [docs]);

  const toAD = (date?: string) => {
    if (!date) return undefined;
    const [y, m, d] = date.split("-");
    return `${Number(y) - 543}-${m}-${d}`;
  };

  const resolvedType =
    type === "__new__" ? customType.trim() : type.trim();

  const onSubmit = async () => {
    if (!file || !resolvedType) {
      setError("กรุณาเลือกไฟล์ PDF และประเภทเอกสาร");
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
        valid_from: toAD(validFrom),
        valid_until: toAD(validUntil),
      });

      router.push(`/merger/${res.id}/view`);
    } catch (err: any) {
      setError(err.message || "อัปโหลดไม่สำเร็จ");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full w-full p-6 max-w-3xl space-y-6">
      <h1 className="text-lg font-semibold text-gray-900">
        เพิ่มเอกสารใหม่
      </h1>

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
          <label className="text-sm font-medium">
            ประเภทเอกสารใหม่
          </label>
          <input
            value={customType}
            onChange={(e) => setCustomType(e.target.value)}
            placeholder="เช่น ระเบียบ"
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
            ใช้ตั้งแต่ (พ.ศ.)
          </label>
          <input
            type="date"
            value={validFrom}
            onChange={(e) => setValidFrom(e.target.value)}
            className="w-full rounded-md border px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="text-sm font-medium">
            ใช้ถึง (พ.ศ.)
          </label>
          <input
            type="date"
            value={validUntil}
            onChange={(e) => setValidUntil(e.target.value)}
            className="w-full rounded-md border px-3 py-2 text-sm"
          />
        </div>
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      <div className="flex justify-end gap-3 pt-4">
        <button
          disabled={loading}
          onClick={onSubmit}
          className="rounded-md bg-blue-600 px-6 py-2
                     text-sm font-medium text-white
                     hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "กำลังอัปโหลด…" : "อัปโหลดเอกสาร"}
        </button>
      </div>
    </div>
  );
}
