"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import Image from "next/image";
import { useParams } from "next/navigation";
import { getDocuments } from "@/libs/doc_manage/getDocuments";
import { getDocStatus } from "@/libs/doc_manage/getDocStatus";

export interface DocMeta {
  id: string;
  title: string;
  type: string;
  announce_date: string;
  effective_date: string;
  version: number | null;
  is_snapshot: boolean;
  is_latest: boolean;
  related_form_id: string[] | null;
  status?: string;
  current_page?: number;
  total_pages?: number;
}

export default function MergerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [docs, setDocs] = useState<DocMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const params = useParams<{ doc_id?: string }>();

  /* ---------------- load docs ---------------- */

  const loadDocuments = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getDocuments();
      setDocs(data);
      setError(null);
    } catch {
      setError("ไม่สามารถโหลดรายการเอกสารได้");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments, params?.doc_id]);

  /* ---------------- event listener ---------------- */

  useEffect(() => {
    const handler = () => loadDocuments();
    window.addEventListener("documents:updated", handler);
    return () => window.removeEventListener("documents:updated", handler);
  }, [loadDocuments]);

  /* ---------------- status polling (OCR / merge) ---------------- */

  useEffect(() => {
    if (!docs.length) return;

    const active = docs.filter(
      (d) => d.status && d.status !== "done" && d.status !== "merged"
    );

    if (!active.length) return;

    const timer = setInterval(async () => {
      setDocs((prev) =>
        prev.map((doc) => {
          if (!doc.status || doc.status === "done") return doc;
          return doc;
        })
      );

      for (const doc of active) {
        try {
          const s = await getDocStatus(doc.id);

          setDocs((prev) =>
            prev.map((d) =>
              d.id === doc.id
                ? {
                    ...d,
                    status: s.status,
                    current_page: s.current_page,
                    total_pages: s.total_pages,
                  }
                : d
            )
          );
        } catch {
          /* ignore */
        }
      }
    }, 3000);

    return () => clearInterval(timer);
  }, [docs]);

  /* ---------------- UI ---------------- */

  return (
    <div className="flex h-screen w-full overflow-hidden bg-white text-[#1e293b]">
      {/* ---------------- sidebar ---------------- */}
      <aside
        className={`flex flex-col border-r border-gray-100 bg-[#f8f9fa] shrink-0 transition-all duration-300
        ${isSidebarOpen ? "w-[280px]" : "w-0 border-none"}`}
      >
        <div className="flex items-center justify-between p-5 pb-2">
          <h1 className="text-xl font-bold">Document Manager</h1>
        </div>

        <div className="px-2 py-2">
          <Link href="/merger/new">
            <div className="flex cursor-pointer items-center gap-3 rounded-full bg-[#dfe1e5] px-4 py-3 hover:bg-gray-300">
              ➕ <span className="font-bold text-[#a83b3b]">เอกสารใหม่</span>
            </div>
          </Link>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-2">
          <h2 className="mb-2 text-xs font-medium text-gray-500 px-2">
            Documents
          </h2>

          {loading && (
            <p className="px-4 text-xs text-gray-500">กำลังโหลด…</p>
          )}
          {error && (
            <p className="px-4 text-xs text-red-500">{error}</p>
          )}

          <div className="space-y-2 pb-10">
            {docs.map((doc) => {
              const percent =
                doc.current_page && doc.total_pages
                  ? Math.round(
                      (doc.current_page / doc.total_pages) * 100
                    )
                  : 0;

              return (
                <Link
                  key={doc.id}
                  href={`/merger/${doc.id}/view`}
                  className={`block rounded-xl px-4 py-2 transition
                    ${
                      params?.doc_id === doc.id
                        ? "bg-[#e8eaed] font-semibold"
                        : "hover:bg-[#e8eaed]"
                    }`}
                >
                  <p className="truncate text-sm text-gray-700">
                    {doc.title}
                  </p>
                  <p className="truncate text-xs text-gray-400">
                    {doc.type} • ฉบับที่ {doc.version ?? "-"}
                  </p>

                  {doc.status && doc.status !== "done" && doc.status !== "merged" && (
                    <div className="mt-1">
                      <p className="text-[11px] text-blue-500">
                        {doc.status === "processing"
                          ? `OCR ${doc.current_page ?? "?"}/${doc.total_pages ?? "?"}`
                          : "กำลังประมวลผล…"}
                      </p>
                      <div className="h-1 w-full rounded bg-gray-200 overflow-hidden">
                        <div
                          className="h-full bg-blue-500 transition-all"
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    </div>
                  )}
                </Link>
              );
            })}
          </div>
        </div>
      </aside>

      {/* ---------------- main ---------------- */}
      <main className="flex flex-1 flex-col relative h-full w-full bg-white">
        <header className="flex h-16 w-full items-center justify-between border-b border-gray-100 bg-white px-4 shrink-0 z-50">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="cursor-pointer truncate flex h-10 w-10 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" >
                <line x1="3" x2="21" y1="6" y2="6" /><line x1="3" x2="21" y1="12" y2="12" /><line x1="3" x2="21" y1="18" y2="18" />
              </svg>
            </button>
            <Link href="/chatbot">
              <div
                className="cursor-pointer truncate flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 shrink-0" >
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" >
                  <path d="M10 2v3" /><path d="M14 2v3" /><path d="M15 11V6h3l2 3v11c0 1.1-.9 2-2 2H6c-1.1 0-2-.9-2-2V9l2-3h3v5c0 1.1.9 2 2 2h2c1.1 0 2-.9 2-2Z" /><path d="M10 18h4" />
                </svg>
                Chatbot
              </div>
            </Link>
            <Link href="/merger">
              <div
                className="cursor-pointer truncate flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 shrink-0" >
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" >
                  <path d="M10 2v3" /><path d="M14 2v3" /><path d="M15 11V6h3l2 3v11c0 1.1-.9 2-2 2H6c-1.1 0-2-.9-2-2V9l2-3h3v5c0 1.1.9 2 2 2h2c1.1 0 2-.9 2-2Z" /><path d="M10 18h4" />
                </svg>
                Document manager
              </div>
            </Link>
          </div>

          <Image
            src="/user-placeholder.jpg"
            alt="User"
            width={40}
            height={40}
            className="rounded-full"
          />
        </header>

        <div className="flex-1 overflow-hidden">{children}</div>
      </main>
    </div>
  );
}
