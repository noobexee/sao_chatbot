"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";

const initialHistory = [
  { id: "1", title: "การตรวจสอบงบประมาณ 2567" },
  { id: "2", title: "รายงานการเงินบริษัท A" },
  { id: "3", title: "เอกสารระเบียบการจัดซื้อ" },
];

export default function AuditLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [history, setHistory] = useState(initialHistory);
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);
  const router = useRouter();

  const toggleMenu = (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    setActiveMenuId((prev) => (prev === id ? null : id));
  };

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    setHistory(prev => prev.filter(item => item.id !== id));
    setActiveMenuId(null);
  };

  useEffect(() => {
    const handler = (ev: MouseEvent) => {
      if (!activeMenuId) return;
      const target = ev.target as Node | null;
      
      const btn = document.querySelector(`[data-menu-btn-id="${activeMenuId}"]`);
      const panel = document.querySelector(`[data-menu-panel-id="${activeMenuId}"]`);
      
      if (!btn || !panel) {
        setActiveMenuId(null);
        return;
      }
      if (btn.contains(target) || panel.contains(target)) {
        return;
      }
      setActiveMenuId(null);
    };

    document.addEventListener("mousedown", handler, true);
    return () => document.removeEventListener("mousedown", handler, true);
  }, [activeMenuId]);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-white text-[#1e293b]">
      <aside
        className={`
          flex flex-col border-r border-gray-100 bg-[#f8f9fa] shrink-0 transition-all duration-300 ease-in-out
          ${isSidebarOpen ? "w-[280px]" : "w-0 border-none"}
        `}
        style={{ overflow: "visible" }}
      >
        <div className="flex items-center justify-between p-5 pb-2 whitespace-nowrap">
          <h1 className="text-xl font-bold text-[#1e293b]">Audit Documents</h1>
          <button
            type="button"
            onClick={() => setIsSidebarOpen(false)}
            className="cursor-pointer truncate text-gray-600 hover:text-black md:hidden"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>
        </div>

        <div className="px-2 py-2 whitespace-nowrap">
          <Link href="/audit">
            <div className="cursor-pointer truncate flex w-full items-center gap-3 rounded-full bg-[#dfe1e5] px-4 py-3 text-left transition-colors hover:bg-gray-300">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10 2v3" /><path d="M14 2v3" /><path d="M15 11V6h3l2 3v11c0 1.1-.9 2-2 2H6c-1.1 0-2-.9-2-2V9l2-3h3v5c0 1.1.9 2 2 2h2c1.1 0 2-.9 2-2Z" /><path d="M10 18h4" />
              </svg>
              <span className="font-bold text-[#a83b3b]">New Audit Project</span>
            </div>
          </Link>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-2 min-w-[280px]">
          <h2 className="mb-2 text-xs font-medium text-gray-500 px-2">ล่าสุด</h2>
          <div className="space-y-1 pb-10">
            {history.map((item) => (
              <div
                key={item.id}
                className={`group relative flex items-center justify-between rounded-full hover:bg-[#e8eaed] transition-colors overflow-visible ${activeMenuId === item.id ? 'z-20 bg-[#e8eaed]' : 'z-0'}`}
              >
                <Link href={`/audit/${item.id}`} className="flex-1 truncate py-2 pl-4 pr-1">
                  <p className="truncate text-sm text-gray-700">{item.title}</p>
                </Link>

                <div className="relative shrink-0 pr-2">
                  <button
                    type="button"
                    data-menu-btn-id={item.id}
                    onClick={(e) => toggleMenu(e, item.id)}
                    className={`p-1 rounded-full hover:bg-gray-300 text-gray-50 transition-all
                        ${activeMenuId === item.id ? "opacity-100 bg-gray-300 block" : "opacity-0 group-hover:opacity-100"}
                      `}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" className="text-gray-600">
                      <circle cx="12" cy="12" r="2" /><circle cx="12" cy="5" r="2" /><circle cx="12" cy="19" r="2" />
                    </svg>
                  </button>

                  {activeMenuId === item.id && (
                    <div
                      data-menu-panel-id={item.id}
                      className="absolute right-0 top-8 z-[999] w-40 overflow-hidden rounded-lg border border-gray-200 bg-[#f8f9fa] shadow-xl"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        type="button"
                        className="flex w-full items-center gap-3 px-4 py-3 text-sm text-gray-800 hover:bg-gray-200 transition-colors text-left"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                        }}
                      >
                        View Details
                      </button>

                      <button
                        type="button"
                        className="flex w-full items-center gap-3 px-4 py-3 text-sm text-red-600 hover:bg-red-100 transition-colors text-left"
                        onClick={(e) => handleDelete(e, item.id)}
                      >
                        Delete
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </aside>

      <main className="flex flex-1 flex-col relative h-full w-full min-w-0 bg-white">
        <header className="flex h-16 w-full items-center justify-between border-b border-gray-100 bg-white px-4 shrink-0 z-50">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="cursor-pointer truncate flex h-10 w-10 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 transition-colors shrink-0"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" x2="21" y1="6" y2="6" /><line x1="3" x2="21" y1="12" y2="12" /><line x1="3" x2="21" y1="18" y2="18" />
              </svg>
            </button>

            <Link href="/chatbot">
              <div className="cursor-pointer truncate flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 shrink-0">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
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
            <span className="absolute bottom-0 right-0 block h-3 w-3 rounded-full bg-green-500 ring-2 ring-white"></span>
          </div>
        </header>

        <div className="flex-1 relative w-full overflow-hidden">{children}</div>
      </main>
    </div>
  );
}