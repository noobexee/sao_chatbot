"use client";

import React, { useState } from "react";
import Link from "next/link";
import Image from "next/image";

interface Doc {
  doc_id: string;
  title: string;
  updated_at: string;
}

const MOCK_DOCS: Doc[] = [
  { doc_id: "1", title: "ระเบียบ สตง. 2566", updated_at: "2025-01-10" },
  { doc_id: "2", title: "ระเบียบ สตง. (ฉบับ 2) 2568", updated_at: "2025-01-12" },
];

export default function MergerLayout({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [activeDocId, setActiveDocId] = useState<string | null>("1");

  return (
    <div className="flex h-screen w-full overflow-hidden bg-white text-[#1e293b]">

      {/* ================= SIDEBAR (CLONE CHATBOT) ================= */}
      <aside
        className={`
          flex flex-col border-r border-gray-100 bg-[#f8f9fa] shrink-0
          transition-all duration-300 ease-in-out
          ${isSidebarOpen ? "w-[280px]" : "w-0 border-none"}
        `}
      >
        <div className="flex items-center justify-between p-5 pb-2 whitespace-nowrap">
          <h1 className="text-xl font-bold text-[#1e293b]">SAO Merger</h1>
          <button onClick={() => setIsSidebarOpen(false)} className="md:hidden">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* NEW DOCUMENT BUTTON — SAME STYLE AS "แชทใหม่" */}
        <div className="px-2 py-2 whitespace-nowrap">
          <button className="cursor-pointer truncate flex w-full items-center gap-3 rounded-full bg-[#dfe1e5] px-4 py-3 text-left transition-colors hover:bg-gray-300">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor">
              <path d="M12 5v14M5 12h14" />
            </svg>
            <span className="font-bold text-[#a83b3b]">เอกสารใหม่</span>
          </button>
        </div>

        {/* DOCUMENT LIST — SAME STRUCTURE AS CHAT HISTORY */}
        <div className="flex-1 overflow-y-auto px-3 py-2">
          <h2 className="mb-2 text-xs font-medium text-gray-500 px-2">
            Documents
          </h2>

          <div className="space-y-1 pb-10">
            {MOCK_DOCS.map((doc) => (
              <div
                key={doc.doc_id}
                onClick={() => setActiveDocId(doc.doc_id)}
                className={`cursor-pointer flex items-center rounded-full transition-colors ${
                  activeDocId === doc.doc_id
                    ? "bg-[#e8eaed] font-semibold"
                    : "hover:bg-[#e8eaed]"
                }`}
              >
                <div className="flex-1 truncate py-2 pl-4 pr-2">
                  <p className="truncate text-sm text-gray-700">
                    {doc.title}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </aside>

      {/* ================= MAIN (CLONE CHATBOT) ================= */}
      <main className="flex flex-1 flex-col relative h-full w-full bg-white">
        <header className="flex h-16 w-full items-center justify-between border-b border-gray-100 bg-white px-4 shrink-0 z-50">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="cursor-pointer truncate flex h-10 w-10 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="3" x2="21" y1="6" y2="6" />
                <line x1="3" x2="21" y1="12" y2="12" />
                <line x1="3" x2="21" y1="18" y2="18" />
              </svg>
            </button>

            <Link href="/chatbot">
              <div className="cursor-pointer truncate flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                Chat
              </div>
            </Link>
          </div>
          
          <div className="cursor-pointer truncate relative h-10 w-10 shrink-0 overflow-hidden rounded-full border border-gray-200 bg-gray-100">
            <Image
              src="/user-placeholder.jpg"
              alt="User"
              width={40}
              height={40}
              className="object-cover w-full h-full"
            />
            <span className="absolute bottom-0 right-0 block h-3 w-3 rounded-full bg-green-500 ring-2 ring-white" />
          </div>
        </header>

        <div className="flex-1 relative w-full overflow-hidden">
          {children}
        </div>
      </main>
    </div>
  );
}
