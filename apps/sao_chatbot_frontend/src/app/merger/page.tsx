"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getDocuments, DocumentMeta } from "@/libs/doc_manage/getDocuments";

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

  const filteredDocs = docs
    // business rule
    .filter(
      (doc) => doc.is_latest === true || doc.status === "need_attention"
    )
    // search
    .filter((doc) =>
      doc.title.toLowerCase().includes(query.toLowerCase())
    );

  return (
    <div className="h-full w-full p-6 flex flex-col space-y-4">

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
        <div className="flex-1 overflow-y-auto space-y-2 pr-1">

          {filteredDocs.length === 0 && (
            <p className="text-sm text-gray-500">
              ไม่พบเอกสารที่ตรงเงื่อนไข
            </p>
          )}

          {filteredDocs.map((doc) => {
            const needAttention = doc.status === "need_attention";

            return (
              <div
                key={doc.id}
                onClick={() => router.push(`/merger/${doc.id}/view`)}
                className={`
                  cursor-pointer rounded-md border px-4 py-3
                  transition hover:bg-gray-50
                  ${
                    needAttention
                      ? "border-yellow-300 bg-yellow-50 hover:bg-yellow-100"
                      : "border-gray-200"
                  }
                `}
              >
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">

                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-gray-800">
                        {doc.title}
                      </p>

                      {doc.is_snapshot && (
                        <span
                          className="rounded-full bg-gray-200 px-2 py-0.5
                                     text-[10px] font-semibold text-gray-700"
                        >
                          SNAPSHOT
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-gray-500">
                      {doc.type} • ฉบับที่ {doc.version}
                    </p>

                    <p className="text-xs text-gray-400">
                      ใช้ตั้งแต่ {doc.effective_date}
                    </p>

                    {needAttention && (
                      <p className="text-xs font-medium text-yellow-700">
                        ต้องตรวจสอบเอกสารนี้
                      </p>
                    )}
                  </div>

                  {needAttention && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/merger/${doc.id}/update`);
                      }}
                      className="rounded-full border border-yellow-400
                                 bg-yellow-100 px-4 py-2 text-sm
                                 hover:bg-yellow-200 transition"
                    >
                      Update
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}