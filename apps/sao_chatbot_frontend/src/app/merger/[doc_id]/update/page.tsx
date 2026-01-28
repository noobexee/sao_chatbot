"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getDocuments, DocumentMeta } from "@/libs/doc_manage/getDocuments";
import { updateSnapshot } from "@/libs/doc_manage/updateSnapshot";
import { getDocMeta, DocMeta } from "@/libs/doc_manage/getDocMeta";

type MergePreference = "edit_context" | "replace_all";

export default function UpdateDocPage() {
  const params = useParams<{ doc_id?: string }>();
  const router = useRouter();
  const baseDocId = params?.doc_id;

  const [baseDoc, setBaseDoc] = useState<DocMeta | null>(null);
  const [docs, setDocs] = useState<DocumentMeta[]>([]);
  const [selectedDocId, setSelectedDocId] = useState("");
  const [preference, setPreference] =
    useState<MergePreference>("edit_context");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!baseDocId) return;

    getDocMeta(baseDocId).then(setBaseDoc);
    getDocuments().then(setDocs);
  }, [baseDocId]);

  const compatibleDocs = docs.filter(
    (d) => d.type === baseDoc?.type && d.id !== baseDocId
  );

  const onSubmit = async () => {
    if (!baseDocId || !selectedDocId) return;

    setLoading(true);
    setError(null);

    try {
      const result = await updateSnapshot(
        baseDocId,
        selectedDocId,
        preference // 👈 merge preference
      );

      if (!result?.id) {
        throw new Error("ไม่พบ snapshot id ที่สร้างใหม่");
      }

      router.push(
        `/merger/compare?base=${encodeURIComponent(
          baseDocId
        )}&snapshot=${encodeURIComponent(result.id)}`
      );
    } catch (e: any) {
      setError(e.message || "อัปเดตเอกสารไม่สำเร็จ");
      setLoading(false);
    }
  };

  if (!baseDocId || !baseDoc) {
    return <div className="p-6 text-gray-500">กำลังโหลด…</div>;
  }

  return (
    <div className="h-full w-full max-w-3xl p-6 space-y-6">
      <h1 className="text-lg font-semibold">
        อัปเดตเอกสาร (Snapshot)
      </h1>

      {/* ===== Select amend document ===== */}
      <div className="space-y-2">
        <label className="text-sm font-medium">
          เอกสารฉบับแก้ไข
        </label>
        <select
          value={selectedDocId}
          onChange={(e) => setSelectedDocId(e.target.value)}
          className="w-full rounded-md border px-3 py-2 text-sm"
        >
          <option value="">— เลือกเอกสาร —</option>
          {compatibleDocs.map((doc) => (
            <option key={doc.id} value={doc.id}>
              {doc.title} • ฉบับที่ {doc.version}
            </option>
          ))}
        </select>
      </div>

      {/* ===== Merge preference ===== */}
      <div className="space-y-2">
        <p className="text-sm font-medium">รูปแบบการ Merge</p>

        <label className="flex items-start gap-2 text-sm">
          <input
            type="radio"
            checked={preference === "edit_context"}
            onChange={() => setPreference("edit_context")}
          />
          <span>
            <b>แก้เฉพาะเนื้อหาที่เปลี่ยน</b>
            <br />
            <span className="text-xs text-gray-500">
              ใช้โครงสร้างเดิม และแทนที่เฉพาะส่วนที่มีการแก้ไข
            </span>
          </span>
        </label>

        <label className="flex items-start gap-2 text-sm">
          <input
            type="radio"
            checked={preference === "replace_all"}
            onChange={() => setPreference("replace_all")}
          />
          <span>
            <b>แทนที่ทั้งฉบับ</b>
            <br />
            <span className="text-xs text-gray-500">
              ใช้เอกสารฉบับแก้ไขแทนเอกสารเดิมทั้งหมด
            </span>
          </span>
        </label>
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      <div className="flex justify-end pt-4">
        <button
          disabled={loading || !selectedDocId}
          onClick={onSubmit}
          className="rounded-md bg-blue-600 px-6 py-2 text-sm text-white
                     hover:bg-blue-700 disabled:opacity-50"
        >
          สร้าง Snapshot
        </button>
      </div>
    </div>
  );
}
