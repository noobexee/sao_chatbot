"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getDocuments, Doc } from "@/libs/doc_manage/getDocuments";
import { updateSnapshot } from "@/libs/doc_manage/updateSnapshot";
import { getDocMeta } from "@/libs/doc_manage/getDocMeta";

type AmendSource = "existing" | "upload";

export default function UpdateDocPage() {
  const params = useParams<{ doc_id?: string }>();
  const router = useRouter();
  const baseDocId = params?.doc_id;
  const [baseDoc, setBaseDoc] = useState<Doc | null>(null);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [source, setSource] = useState<AmendSource>("existing");
  const [selectedDocId, setSelectedDocId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!baseDocId) return;

    getDocMeta(baseDocId).then((meta) => {
      setBaseDoc(meta as any);
      setTitle(meta.title);
    });

    getDocuments().then(setDocs);
  }, [baseDocId]);

  const compatibleDocs = docs.filter(
    (d) => d.type === baseDoc?.type && d.id !== baseDocId
  );

  const onSubmit = async () => {
    if (!baseDocId) return;

    setLoading(true);
    setError(null);

    try {
      let amendDocId: string;

      if (source === "existing") {
        if (!selectedDocId) {
          throw new Error("กรุณาเลือกเอกสาร");
        }
        amendDocId = selectedDocId;
      } else {
        throw new Error("โหมด upload ต้องสร้างเอกสารก่อนแล้วจึง merge");
      }

      const result = await updateSnapshot(baseDocId, amendDocId);

      if (!result?.id) {
        throw new Error("ไม่พบ snapshot id ที่สร้างใหม่");
      }

      // ✅ FIX: redirect ไป compare
      router.push(
        `merger/compare?base=${encodeURIComponent(
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

      <div className="space-y-2">
        <p className="text-sm font-medium">เอกสารฉบับแก้ไข</p>
        <div className="flex gap-4 text-sm">
          <label className="flex items-center gap-2">
            <input
              type="radio"
              checked={source === "existing"}
              onChange={() => setSource("existing")}
            />
            มีอยู่แล้วในระบบ
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              checked={source === "upload"}
              onChange={() => setSource("upload")}
            />
            อัปโหลดใหม่
          </label>
        </div>
      </div>

      {source === "existing" && (
        <div className="space-y-2">
          <label className="text-sm font-medium">เลือกเอกสาร</label>
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
      )}

      {source === "upload" && (
        <>
          <div className="space-y-2">
            <label className="text-sm font-medium">ชื่อเอกสาร</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-md border px-3 py-2 text-sm"
            />
            <p className="text-xs text-gray-500">
              ค่าเริ่มต้นคือชื่อเอกสารต้นฉบับ
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">ไฟล์ PDF</label>
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block w-full text-sm"
            />
          </div>
        </>
      )}

      {error && <p className="text-sm text-red-500">{error}</p>}

      <div className="flex justify-end pt-4">
        <button
          disabled={loading}
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
