"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import getUserHistory from "@/libs/getUserHistory"; 

  // Define the shape of your API data based on the JSON you provided
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
  const [history, setHistory] = useState<Session[]>([]); // Typed as Session[]
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);
  const router = useRouter();
  const params = useParams();

  // Hardcoded for now (until you have AuthContext)
  const USER_ID = "1"; 

  // 1. FETCH SESSIONS WITH YOUR NEW LIB
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        // Call your lib function
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
      {/* SIDEBAR */}
      <aside
        className={`
          flex flex-col border-r border-gray-100 bg-[#f8f9fa] shrink-0 transition-all duration-300 ease-in-out
          ${isSidebarOpen ? "w-[280px]" : "w-0 border-none"}
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 pb-2 whitespace-nowrap">
          <h1 className="text-xl font-bold text-[#1e293b]">SAO Chatbot</h1>
          <button onClick={() => setIsSidebarOpen(false)} className="md:hidden">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>
        </div>

        {/* New Chat Button */}
        <div className="px-2 py-2 whitespace-nowrap">
          <Link href="/chatbot"> 
            <div className="cursor-pointer flex w-full items-center gap-3 rounded-full bg-[#dfe1e5] px-4 py-3 hover:bg-gray-300 transition-colors">
              <span className="font-bold text-[#a83b3b]">+ New Chat</span>
            </div>
          </Link>
        </div>

        {/* History List */}
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
                
                {/* Menu Button (Only shows on hover or active) */}
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
          </div>
           <div className="h-10 w-10 rounded-full bg-gray-200 overflow-hidden border border-gray-300">
             <img src="/user-placeholder.jpg" alt="User" className="w-full h-full object-cover" />
           </div>
        </header>
        
         <div className="flex-1 relative w-full overflow-hidden">
            {children}
         </div>
      </main>
    </div>
  );
}