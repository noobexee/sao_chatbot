"use client";

import { useParams } from "next/navigation";

export default function UpdateDocPage() {
  const { docId } = useParams();

  return (
    <div className="h-full w-full p-6 space-y-4">
      <h1 className="text-lg font-semibold">
        อัปเดตเอกสาร {docId}
      </h1>

      <p className="text-sm text-gray-600">
        อัปโหลดเอกสารฉบับแก้ไข (amendment)
      </p>

      <input
        type="file"
        accept=".pdf"
        className="block w-full text-sm"
      />

      <button className="rounded-md bg-blue-600 px-4 py-2 text-white text-sm">
        อัปเดตเอกสาร
      </button>
    </div>
  );
}
