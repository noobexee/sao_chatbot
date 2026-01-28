"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getDocuments, DocumentMeta } from "@/libs/doc_manage/getDocuments";

/**
 * Backend returns:
 * {
 *   id,
 *   ...DocumentMeta,
 *   status
 * }
 */
type DocumentWithStatus = DocumentMeta & {
  id: string;
  status: string;
};

export default function MergerHomePage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [docs, setDocs] = useState<DocumentWithStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const data = await getDocuments();
        setDocs(data as DocumentWithStatus[]);
      } catch {
        setError("ไม่สามารถโหลดรายการเอกสารได้");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const filteredDocs = docs.filter((doc) =>
    doc.title.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="h-full w-full p-6 space-y-4">

      <h2 className="text-sm font-semibold text-gray-800">
        เลือกเอกสารที่ต้องการอัปเดต
      </h2>

      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="ค้นหาเอกสาร"
        className="w-full rounded-md border border-gray-300 px-4 py-2 text-sm
                   focus:outline-none focus:ring-2 focus:ring-blue-500"
      />

      {loading && (
        <p className="text-sm text-gray-500">กำลังโหลดเอกสาร...</p>
      )}

      {error && (
        <p className="text-sm text-red-500">{error}</p>
      )}

      {!loading && !error && (
        <div className="space-y-2">
          {filteredDocs.length === 0 && (
            <p className="text-sm text-gray-500">ไม่พบเอกสาร</p>
          )}

          {filteredDocs.map((doc) => {
            const canUpdate = doc.status === "done";

            return (
              <div
                key={doc.id}
                className="flex items-center justify-between
                           rounded-md border border-gray-200 px-4 py-3"
              >
                <div className="space-y-0.5">
                  <p className="text-sm font-medium text-gray-800">
                    {doc.title}
                  </p>

                  <p className="text-xs text-gray-500">
                    {doc.type} • ฉบับที่ {doc.version}
                  </p>

                  <p className="text-xs text-gray-400">
                    ใช้ตั้งแต่ {doc.effective_date}
                  </p>

                  {doc.status !== "done" && (
                    <p className="text-xs text-blue-500">
                      กำลังประมวลผลเอกสาร…
                    </p>
                  )}
                </div>

                <button
                  disabled={!canUpdate}
                  onClick={() => router.push(`/merger/${doc.id}/update`)}
                  className={`rounded-full border px-4 py-2 text-sm
                    transition
                    ${
                      canUpdate
                        ? "border-gray-200 hover:bg-gray-50"
                        : "border-gray-100 text-gray-400 cursor-not-allowed"
                    }`}
                >
                  Update document
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
