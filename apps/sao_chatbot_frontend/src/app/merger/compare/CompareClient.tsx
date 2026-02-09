"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { diffLines } from "diff";

import { getDocStatus } from "@/libs/doc_manage/getDocStatus";
import { getDocText } from "@/libs/doc_manage/getDocText";
import { getDocMeta } from "@/libs/doc_manage/getDocMeta";
import { saveDocText } from "@/libs/doc_manage/updateDocument";

type MergeStatus = "merging" | "merged";

type DocMeta = {
  title: string;
  type: string;
  announce_date: string;
  effective_date?: string;
};

export default function CompareClient() {
  const router = useRouter();
  const params = useSearchParams();

  const baseId = params.get("base");
  const snapshotId = params.get("snapshot");

  const [status, setStatus] = useState<MergeStatus>("merging");
  const [saving, setSaving] = useState(false);

  const [baseText, setBaseText] = useState("");
  const [mergedText, setMergedText] = useState("");

  const [meta, setMeta] = useState<DocMeta | null>(null);
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

  /* ================= Load texts ================= */
  useEffect(() => {
    if (status !== "merged" || !baseId || !snapshotId) return;

    Promise.all([
      getDocText(baseId),
      getDocText(snapshotId),
      getDocMeta(snapshotId),
    ])
      .then(([oldTxt, newTxt, meta]) => {
        setBaseText(oldTxt);
        setMergedText(newTxt);
        setMeta({
          title: meta.title,
          type: meta.type,
          announce_date: meta.announce_date,
          effective_date: meta.effective_date ?? undefined,
        });
      })
      .catch(() => {
        setError("ไม่สามารถโหลดเอกสารได้");
      });
  }, [status, baseId, snapshotId]);

  if (!baseId || !snapshotId) {
    return <div className="p-6 text-gray-500">ข้อมูลไม่ครบ</div>;
  }

  return (
    <div className="flex h-full w-full flex-col">
      {/* ================= Header ================= */}
      <div className="flex items-center justify-between border-b px-6 py-4">
        <h1 className="text-lg font-semibold">
          เปรียบเทียบเอกสาร (Old vs New)
        </h1>

        {status === "merged" && (
          <button
            disabled={saving || !meta}
            onClick={async () => {
              if (!snapshotId || !meta) return;

              try {
                setSaving(true);

                await saveDocText(snapshotId, {
                  content: mergedText,
                  title: meta.title,
                  type: meta.type,
                  announce_date: meta.announce_date,
                  effective_date: meta.effective_date,
                });

                router.push(`${snapshotId}/view`);
              } catch (err) {
                alert(
                  err instanceof Error
                    ? err.message
                    : "บันทึกเอกสารไม่สำเร็จ"
                );
              } finally {
                setSaving(false);
              }
            }}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "กำลังบันทึก…" : "เสร็จสิ้น"}
          </button>
        )}
      </div>

      {/* ================= Status ================= */}
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

      {/* ================= Diff ================= */}
      {status === "merged" && !error && (
        <div className="flex-1 overflow-auto px-6 pb-6">
          <DiffSideBySide
            oldText={baseText}
            newText={mergedText}
            onChangeNew={setMergedText}
          />
        </div>
      )}
    </div>
  );
}

/* ======================= Side-by-side Diff ======================= */

function DiffSideBySide({
  oldText,
  newText,
  onChangeNew,
}: {
  oldText: string;
  newText: string;
  onChangeNew: (v: string) => void;
}) {
  const ref = useRef<HTMLPreElement>(null);
  const [editing, setEditing] = useState(false);

  /* ---------- Diff HTML (read-only mode only) ---------- */
  const newHtml = useMemo(() => {
    if (editing) return "";
    return diffLines(oldText, newText)
      .filter((p) => !p.removed)
      .map((p) => {
        const cls = p.added
          ? "bg-green-100 text-green-800"
          : "text-gray-800";
        return `<span class="${cls}">${escapeHtml(p.value)}</span>`;
      })
      .join("");
  }, [oldText, newText, editing]);

  const oldHtml = useMemo(() => {
    return diffLines(oldText, newText)
      .filter((p) => !p.added)
      .map((p) => {
        const cls = p.removed
          ? "bg-red-100 text-red-800"
          : "text-gray-800";
        return `<span class="${cls}">${escapeHtml(p.value)}</span>`;
      })
      .join("");
  }, [oldText, newText]);

  /* ---------- Enter edit mode ---------- */
  const startEdit = () => {
    setEditing(true);
    requestAnimationFrame(() => {
      if (ref.current) {
        ref.current.innerText = newText;
        ref.current.focus();
      }
    });
  };

  /* ---------- Exit edit mode ---------- */
  const finishEdit = () => {
    if (!ref.current) return;
    const text = ref.current.innerText;
    onChangeNew(text);
    setEditing(false);
  };

  return (
    <div className="flex h-full gap-2">
      {/* ===== Old ===== */}
      <div className="flex w-1/2 resize-x overflow-auto rounded-md border min-w-[300px]">
        <div className="flex w-full flex-col">
          <div className="border-b bg-gray-50 px-3 py-2 text-sm font-medium">
            Old
          </div>
          <pre
            className="flex-1 whitespace-pre-wrap font-mono text-sm p-3"
            dangerouslySetInnerHTML={{ __html: oldHtml }}
          />
        </div>
      </div>

      {/* ===== New ===== */}
      <div className="flex w-1/2 resize-x overflow-auto rounded-md border min-w-[300px]">
        <div className="flex w-full flex-col">
          <div className="border-b bg-gray-50 px-3 py-2 text-sm font-medium">
            New {editing ? "(editing)" : "(Double-click to edit)"}
          </div>

          <pre
            ref={ref}
            contentEditable={editing}
            suppressContentEditableWarning
            onDoubleClick={startEdit}
            onBlur={finishEdit}
            className={`flex-1 whitespace-pre-wrap font-mono text-sm p-3 outline-none ${
              editing
                ? "ring-2 ring-blue-200"
                : ""
            }`}
            dangerouslySetInnerHTML={
              editing ? undefined : { __html: newHtml }
            }
          />
        </div>
      </div>
    </div>
  );
}


/* ================= Utils ================= */

function escapeHtml(text: string) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
