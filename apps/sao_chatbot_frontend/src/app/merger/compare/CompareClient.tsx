"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { diffLines } from "diff";

import { getDocStatus } from "@/libs/doc_manage/getDocStatus";
import { getDocText } from "@/libs/doc_manage/getDocText";

type MergeStatus = "merging" | "merged";

export default function CompareClient() {
  const params = useSearchParams();
  const baseId = params.get("base");
  const snapshotId = params.get("snapshot");

  const [status, setStatus] = useState<MergeStatus>("merging");
  const [baseText, setBaseText] = useState("");
  const [mergedText, setMergedText] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!snapshotId || status === "merged") return;

    const poll = async () => {
      try {
        const data = await getDocStatus(snapshotId);
        setStatus(data.status === "merged" ? "merged" : "merging");
      } catch {
        // ignore while merging
      }
    };

    poll();
    const timer = setInterval(poll, 2000);
    return () => clearInterval(timer);
  }, [snapshotId, status]);

  useEffect(() => {
    if (status !== "merged" || !baseId || !snapshotId) return;

    Promise.all([
      getDocText(baseId),
      getDocText(snapshotId),
    ])
      .then(([oldTxt, newTxt]) => {
        setBaseText(oldTxt);
        setMergedText(newTxt);
      })
      .catch(() => {
        setError("ไม่สามารถโหลดไฟล์เอกสารได้");
      });
  }, [status, baseId, snapshotId]);

  if (!baseId || !snapshotId) {
    return <div className="p-6 text-gray-500">ข้อมูลไม่ครบ</div>;
  }

  return (
    <div className="flex h-full w-full flex-col">
      {/* ===== Header ===== */}
      <div className="border-b px-6 py-4">
        <h1 className="text-lg font-semibold">
          เปรียบเทียบเอกสาร (Old vs Merged)
        </h1>
      </div>

      {/* ===== Status ===== */}
      {status === "merging" && (
        <div className="m-6 rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700">
          <span className="animate-pulse">⏳</span>{" "}
          กำลังรวมเอกสาร — metadata พร้อมแล้ว
        </div>
      )}

      {error && (
        <div className="m-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* ===== Diff ===== */}
      {status === "merged" && !error && (
        <div className="flex-1 overflow-auto px-6 pb-6">
          <DiffView oldText={baseText} newText={mergedText} />
        </div>
      )}
    </div>
  );
}

function DiffView({
  oldText,
  newText,
}: {
  oldText: string;
  newText: string;
}) {
  const diffs = diffLines(oldText, newText);

  return (
    <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed">
      {diffs.map((part, idx) => (
        <span
          key={idx}
          className={
            part.added
              ? "bg-green-100 text-green-800"
              : part.removed
              ? "bg-red-100 text-red-800"
              : "text-gray-800"
          }
        >
          {part.value}
        </span>
      ))}
    </pre>
  );
}
