"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";

interface Doc {
  doc_id: string;
  title: string;
  updated_at: string;
}

const MOCK_DOCS: Doc[] = [
  { doc_id: "1", title: "ระเบียบ สตง. 2566.pdf", updated_at: "2025-01-10"},
  { doc_id: "2", title: "ระเบียบ สตง. (ฉบับ 2) 2568.pdf", updated_at: "2025-01-12" },
];

export default function MergerHomePage() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  const filteredDocs = MOCK_DOCS.filter((doc) =>
    doc.title.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="h-full w-full p-6 space-y-4">

      <h2 className="text-sm font-semibold text-gray-800">
        เลือกเอกสารที่ต้องการอัปเดต
      </h2>

      {/* SEARCH */}
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="ค้นหาเอกสาร (.pdf)"
        className="w-full rounded-md border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />

      {/* DOCUMENT LIST */}
      <div className="space-y-2">
        {filteredDocs.map((doc) => (
          <div
            key={doc.doc_id}
            className="flex items-center justify-between rounded-md border border-gray-200 px-4 py-3"
          >
            <div>
              <p className="text-sm font-medium text-gray-800">
                {doc.title}
              </p>
              <p className="text-xs text-gray-500">
                Updated {doc.updated_at}
              </p>
            </div>

            <button
              onClick={() => router.push(`/merger/${doc.doc_id}`)}
              className="rounded-full border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50"
            >
              Update document
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
