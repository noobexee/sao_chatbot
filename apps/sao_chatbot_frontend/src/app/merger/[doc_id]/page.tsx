"use client";

import React, { useState } from "react";
import { useParams } from "next/navigation";

export default function UpdateDocumentPage() {
  const { doc_id } = useParams<{ doc_id: string }>();

  const [ocrText, setOcrText] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // mock OCR
  const mockOCR = async (file: File) => {
    return `OCR TEXT\nไฟล์: ${file.name}\n\nแก้ไขข้อความได้ที่นี่`;
  };

  const handleUpload = async (file: File) => {
    setFileName(file.name);
    const text = await mockOCR(file);
    setOcrText(text);
  };

  // ✅ PREPARED BACKEND FUNCTION
  const saveToDocument = async () => {
    setSaving(true);

    const payload = {
      doc_id,
      content_txt: ocrText.trim(),
    };

    console.log("SEND TO BACKEND:", payload);

    // await fetch("/api/document/update", {
    //   method: "POST",
    //   body: JSON.stringify(payload),
    // });

    setSaving(false);
    alert("บันทึกเอกสารเรียบร้อย");
  };

  return (
    <div className="h-full w-full overflow-y-auto p-6 space-y-6">

      {/* UPLOAD */}
      <div className="rounded-lg border border-dashed border-gray-300 p-6">
        <label className="block text-sm font-medium mb-2">
          Upload updated document
        </label>
        <input
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          onChange={(e) => {
            if (e.target.files?.[0]) {
              handleUpload(e.target.files[0]);
            }
          }}
        />
        {fileName && (
          <p className="mt-2 text-sm text-gray-500">
            Uploaded: {fileName}
          </p>
        )}
      </div>

      {/* OCR */}
      <div>
        <label className="block text-sm font-medium mb-2">
          OCR Result (Editable)
        </label>
        <textarea
          value={ocrText}
          onChange={(e) => setOcrText(e.target.value)}
          className="w-full h-[300px] rounded-lg border border-gray-300 p-4 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* SAVE */}
      <div className="flex justify-end">
        <button
          disabled={!ocrText || saving}
          onClick={saveToDocument}
          className={`rounded-md px-6 py-2 text-sm text-white transition-colors
            ${
              saving
                ? "bg-gray-400"
                : "bg-blue-600 hover:bg-blue-700"
            }
          `}
        >
          Save to document
        </button>
      </div>
    </div>
  );
}
