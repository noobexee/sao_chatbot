"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import getUserHistory from "@/libs/getUserHistory"; 
import Image from "next/image";

interface Session {
  session_id: string;
  title: string;
  created_at: string;
}

interface HistoryApiResponse {
  success: boolean;
  message: string;
  data: Session[];
}

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [history, setHistory] = useState<Session[]>([]); 
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);
  const router = useRouter();
  const params = useParams();

  const USER_ID = "1"; 

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const response: HistoryApiResponse = await getUserHistory(USER_ID);
        
        if (response.success) {
          setHistory(response.data);
        } else {
          console.error("API Error:", response.message);
        }
      } catch (err) {
        console.error("Failed to load sidebar:", err);
      }
    };
    fetchSessions();
  }, []);

  const toggleMenu = (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    setActiveMenuId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-white text-[#1e293b]">
      <aside
        className={`
          flex flex-col border-r border-gray-100 bg-[#f8f9fa] shrink-0 transition-all duration-300 ease-in-out
          ${isSidebarOpen ? "w-[280px]" : "w-0 border-none"}
        `}
      >
        <div className="flex items-center justify-between p-5 pb-2 whitespace-nowrap">
          <h1 className="text-xl font-bold text-[#1e293b]">SAO Chatbot</h1>
          <button onClick={() => setIsSidebarOpen(false)} className="md:hidden">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>
        </div>
          
        <div className="px-2 py-2 whitespace-nowrap">
          <Link href="/chatbot">
            <div className="cursor-pointer truncate flex w-full items-center gap-3 rounded-full bg-[#dfe1e5] px-4 py-3 text-left transition-colors hover:bg-gray-300" >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" className="text-[#333]" >
                <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
              </svg>
              <span className="font-bold text-[#a83b3b]">แชทใหม่</span>
            </div>
          </Link>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-2">
          <h2 className="mb-2 text-xs font-medium text-gray-500 px-2">Recent</h2>
          <div className="space-y-1 pb-10">
            {history.map((item) => (
              <div
                key={item.session_id}
                className={`group relative flex items-center justify-between rounded-full hover:bg-[#e8eaed] transition-colors ${
                  params.sessionId === item.session_id ? "bg-[#e8eaed] font-semibold" : ""
                }`}
              >
                <Link href={`/chatbot/${item.session_id}`} className="flex-1 truncate py-2 pl-4 pr-1">
                  <p className="truncate text-sm text-gray-700">{item.title}</p>
                </Link>
                
                <div className="relative shrink-0 pr-2">
                  <button
                    type="button"
                    onClick={(e) => toggleMenu(e, item.session_id)}
                    className={`p-1 rounded-full hover:bg-gray-300 transition-all
                      ${activeMenuId === item.session_id ? "opacity-100 bg-gray-300 block" : "opacity-0 group-hover:opacity-100"}
                    `}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" className="text-gray-600">
                      <circle cx="12" cy="12" r="2" /><circle cx="12" cy="5" r="2" /><circle cx="12" cy="19" r="2" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </aside>

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
            <Link href="/audit">
              <div
                className="cursor-pointer truncate flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 shrink-0" >
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" >
                  <path d="M10 2v3" /><path d="M14 2v3" /><path d="M15 11V6h3l2 3v11c0 1.1-.9 2-2 2H6c-1.1 0-2-.9-2-2V9l2-3h3v5c0 1.1.9 2 2 2h2c1.1 0 2-.9 2-2Z" /><path d="M10 18h4" />
                </svg>
                Audit
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
        
         <div className="flex-1 relative w-full overflow-hidden">
            {children}
         </div>
      </main>
    </div>
  );
}