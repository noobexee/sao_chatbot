"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getDocMeta, DocMeta } from "@/libs/doc_manage/getDocMeta";
import { getDocText } from "@/libs/doc_manage/getDocText";
import { checkHasPdf } from "@/libs/doc_manage/getDocOriginal";
import { getDocOriginalPreview, PreviewFile } from "@/libs/doc_manage/getOriginalPreview";
import { getDocStatus, DocStatusResponse } from "@/libs/doc_manage/getDocStatus";
import { saveDocText } from "@/libs/doc_manage/uploadText";

type ViewMode = "pdf" | "text";

export default function ViewDocumentPage() {
  const params = useParams<{ doc_id: string }>();
  const docId = params?.doc_id;
  const [meta, setMeta] = useState<DocMeta | null>(null);
  const [editMeta, setEditMeta] = useState<DocMeta | null>(null);
  const [text, setText] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [hasPdf, setHasPdf] = useState(true);
  const [mode, setMode] = useState<ViewMode>("pdf");
  const [status, setStatus] = useState<string>("queued");
  const [page, setPage] = useState<number | null>(null);
  const [totalPages, setTotalPages] = useState<number | null>(null);
  const [message, setMessage] = useState<string | undefined>();
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentFile, setCurrentFile] = useState<PreviewFile | null>(null);

  function isoToDDMMYYYY(value?: string) {
    if (!value) return "";
    const [yyyy, mm, dd] = value.split("-");
    return `${dd}-${mm}-${yyyy}`;
  }
  
  useEffect(() => {
    if (!docId) return;
    getDocMeta(docId).then((m) => {
      setMeta(m);
      setEditMeta(m);
    });
    checkHasPdf(docId).then((ok) => {
      setHasPdf(ok);
      if (!ok) setMode("text");
    });
    getDocText(docId)
      .then((t) => {
        setText(t);
        setDraft(t);
      })
      .catch(() => setText(null));
  }, [docId]);

  useEffect(() => {
    if (!docId || !hasPdf || mode !== "pdf") return;
    getDocOriginalPreview(docId)
      .then(setCurrentFile)
      .catch(() => setCurrentFile(null));
  }, [docId, hasPdf, mode]);

  useEffect(() => {
    return () => {
      if (currentFile?.previewUrl) {
        URL.revokeObjectURL(currentFile.previewUrl);
      }
    };
  }, [currentFile]);
  useEffect(() => {
    if (!docId) return;
    if (status === "done" || status === "merged") return;

    let timer: NodeJS.Timeout;

    const poll = async () => {
      try {
        const res: DocStatusResponse = await getDocStatus(docId);

        setStatus(res.status);
        setPage(res.current_page ?? null);
        setTotalPages(res.total_pages ?? null);
        setMessage(res.message);

        if (res.status === "done" || res.status === "merged") {
          const t = await getDocText(docId);
          setText(t);
          setDraft(t);
          return;
        }

        timer = setTimeout(poll, 3000);
      } catch {
        setError("ไม่สามารถตรวจสอบสถานะ OCR ได้");
      }
    };
    poll();
    return () => clearTimeout(timer);
  }, [docId, status]);
  const onSave = async () => {
    if (!docId || !editMeta) return;
    setSaving(true);
    setError(null);
    try {
      await saveDocText(docId, {
        content: draft,
        title: editMeta.title,
        version: editMeta.version ?? undefined,
        valid_from: editMeta.valid_from,
        valid_until: editMeta.valid_until ?? undefined,
      });
      setMeta(editMeta);
      setText(draft);
      setEditing(false);
    } catch {
      setError("บันทึกข้อมูลไม่สำเร็จ");
    } finally {
      setSaving(false);
    }
  };

  if (!docId) {
    return <div className="p-6 text-red-500">Document ID not found</div>;
  }
  return (
    <div className="flex h-full flex-col p-4 md:p-6">
      <div className="border-b bg-white px-6 py-4 space-y-2">
        {editing ? (
          <input
            value={editMeta?.title ?? ""}
            onChange={(e) =>
              setEditMeta((m) => m && { ...m, title: e.target.value })
            }
            className="w-full border rounded px-3 py-1 text-sm"
          />
        ) : (
          <h1 className="text-base font-semibold">{meta?.title ?? "—"}</h1>
        )}
        {meta && (
          <div className="text-xs text-gray-500 flex gap-2 flex-wrap">
            <span>{meta.type}</span>

            {editing ? (
              <>
                <input
                  className="border rounded px-2"
                  value={editMeta?.version ?? ""}
                  placeholder="ฉบับที่"
                  onChange={(e) =>
                    setEditMeta((m) => m && { ...m, version: e.target.value })
                  }
                />
                <input
                  type="date"
                  className="border rounded px-2"
                  value={editMeta?.valid_from ?? ""}
                  onChange={(e) =>
                    setEditMeta(
                      (m) => m && { ...m, valid_from: e.target.value }
                    )
                  }
                />
                <input
                  type="date"
                  className="border rounded px-2"
                  value={editMeta?.valid_until ?? ""}
                  onChange={(e) =>
                    setEditMeta(
                      (m) => m && { ...m, valid_until: e.target.value }
                    )
                  }
                />
              </>
            ) : (
              <>
                {meta.version && <span>ฉบับที่ {meta.version}</span>}
                {meta.valid_from && <span>ใช้ตั้งแต่ {meta.valid_from}</span>}
                {meta.valid_until && <span>ถึง {meta.valid_until}</span>}
              </>
            )}
          </div>
        )}
        <div className="flex justify-between items-center pt-2">
          <div className="flex rounded-full border overflow-hidden">
            <button
              disabled={!hasPdf}
              onClick={() => setMode("pdf")}
              className={`px-4 py-1 text-sm ${
                !hasPdf
                  ? "text-gray-400"
                  : mode === "pdf"
                  ? "bg-gray-200 font-medium"
                  : ""
              }`}
            >
              PDF
            </button>
            <button
              onClick={() => setMode("text")}
              className={`px-4 py-1 text-sm ${
                mode === "text" ? "bg-gray-200 font-medium" : ""
              }`}
            >
              Text
            </button>
          </div>
          {mode === "text" &&
            (status === "done" || status === "merged") && (
              <div className="flex gap-2">
                {!editing ? (
                  <button
                    onClick={() => {
                      setEditing(true);
                      setEditMeta(meta);
                    }}
                    className="text-sm px-4 py-1 rounded bg-gray-100"
                  >
                    แก้ไข
                  </button>
                ) : (
                  <>
                    <button
                      disabled={saving}
                      onClick={onSave}
                      className="text-sm px-4 py-1 rounded bg-blue-600 text-white"
                    >
                      {saving ? "กำลังบันทึก…" : "บันทึก"}
                    </button>
                    <button
                      onClick={() => {
                        setDraft(text ?? "");
                        setEditMeta(meta);
                        setEditing(false);
                      }}
                      className="text-sm px-4 py-1 rounded bg-gray-100"
                    >
                      ยกเลิก
                    </button>
                  </>
                )}
              </div>
            )}
        </div>
      </div>
      <div className="flex-1 overflow-hidden bg-gray-50">
        {mode === "pdf" && hasPdf && (
          <iframe
            src={currentFile?.previewUrl}
            className="w-full h-full border-none"
          />
        )}
        {mode === "text" && (
          <div className="h-full overflow-auto p-6 bg-white space-y-4">
            {status !== "done" && status !== "merged" && (
              <OCRProgress
                status={status}
                page={page}
                totalPages={totalPages}
                message={message}
              />
            )}
            {error && <p className="text-sm text-red-500">{error}</p>}
            {(status === "done" || status === "merged") &&
              (editing ? (
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  className="w-full h-[70vh] border rounded p-4 font-mono text-sm"
                />
              ) : (
                <pre className="whitespace-pre-wrap text-sm">{text}</pre>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}

function OCRProgress({
  status,
  page,
  totalPages,
  message,
}: {
  status: string;
  page: number | null;
  totalPages: number | null;
  message?: string;
}) {
  const percent =
    page && totalPages ? Math.round((page / totalPages) * 100) : 0;

  return (
    <div className="max-w-md space-y-2">
      <p className="text-sm text-gray-600">
        {message}
        {page && totalPages && <> • หน้า {page}/{totalPages}</>}
      </p>
      <div className="h-2 w-full rounded bg-gray-200">
        <div
          className="h-full bg-blue-500 transition-all"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
