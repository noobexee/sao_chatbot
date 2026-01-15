"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import getUserHistory from "@/libs/getUserHistory"; 
import deleteChatHistory from "@/libs/deleteChatHistory"; 
import { updateSession } from "@/libs/updateUserSession";
import Image from "next/image";

interface Session {
  session_id: string;
  title: string;
  created_at: string;
  is_pinned?: boolean;
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
  
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const renameInputRef = useRef<HTMLInputElement>(null);

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

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setActiveMenuId(null);
    if (activeMenuId) {
      window.addEventListener("click", handleClickOutside);
    }
    return () => window.removeEventListener("click", handleClickOutside);
  }, [activeMenuId]);

  // Focus input when editing starts
  useEffect(() => {
    if (editingId && renameInputRef.current) {
      renameInputRef.current.focus();
    }
  }, [editingId]);

  const toggleMenu = (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    setActiveMenuId((prev) => (prev === id ? null : id));
  };

  // --- Logic for Delete ---
  const handleDeleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.preventDefault();
    e.stopPropagation();

    if (!confirm("คุณต้องการลบแชทนี้ใช่หรือไม่?")) return;

    try {
      const result = await deleteChatHistory(USER_ID, sessionId);
      
      if (result.success) {
        setHistory((prev) => prev.filter((item) => item.session_id !== sessionId));
        if (params.session_id === sessionId) {
          router.push("/chatbot");
        }
      } else {
        alert("ไม่สามารถลบได้: " + result.message);
      }
    } catch (error) {
      console.error("Delete failed:", error);
      alert("เกิดข้อผิดพลาดในการลบ");
    } finally {
      setActiveMenuId(null);
    }
  };

  // --- Logic for Pinning ---
  const handlePin = async (e: React.MouseEvent, session: Session) => {
    e.stopPropagation();
    const newStatus = !session.is_pinned;

    // Optimistic Update with Sorting (Pinned items go to top)
    setHistory(prev => {
      const updatedList = prev.map(item => 
        item.session_id === session.session_id ? { ...item, is_pinned: newStatus } : item
      );

      return updatedList.sort((a, b) => {
        const pinA = a.is_pinned ? 1 : 0;
        const pinB = b.is_pinned ? 1 : 0;
        if (pinA !== pinB) return pinB - pinA; // Higher pin value first
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime(); // Then newest
      });
    });

    setActiveMenuId(null);
    
    // Call API to save to DB
    try {
      await updateSession(USER_ID, session.session_id, { is_pinned: newStatus });
    } catch (error) {
      console.error("Failed to pin session:", error);
      // Optional: Revert UI if needed, currently just logging
    }
  };

  // --- Logic for Renaming ---
  const startRename = (e: React.MouseEvent, session: Session) => {
    e.stopPropagation();
    setEditingId(session.session_id);
    setEditTitle(session.title);
    setActiveMenuId(null);
  };

  const saveRename = async () => {
    if (!editingId) return;
    const sessionId = editingId;
    const newTitle = editTitle.trim();

    if (newTitle) {
      // Optimistic UI Update
      setHistory(prev => prev.map(item => 
        item.session_id === sessionId ? { ...item, title: newTitle } : item
      ));
      
      // Call API to save to DB
      try {
        await updateSession(USER_ID, sessionId, { title: newTitle });
      } catch (error) {
        console.error("Failed to rename session:", error);
      }
    }
    
    setEditingId(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") saveRename();
    if (e.key === "Escape") setEditingId(null);
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
                 {/* Input Field for Renaming OR Link for Navigation */}
                 {editingId === item.session_id ? (
                  <input
                    ref={renameInputRef}
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onBlur={saveRename}
                    onKeyDown={handleKeyDown}
                    className="flex-1 ml-4 mr-2 h-8 bg-white border border-blue-500 rounded px-2 py-1 text-sm outline-none text-gray-700"
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <Link href={`/chatbot/${item.session_id}`} className="flex-1 truncate py-2 pl-4 pr-1 flex items-center gap-2">
                    {/* Pin Icon if pinned */}
                    {item.is_pinned && (
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="currentColor" className="text-gray-500 shrink-0 transform rotate-45">
                         <path d="M16 2V4H17V13L19 15V17H13V22H11V17H5V15L7 13V4H8V2H16Z" />
                      </svg>
                    )}
                    <p className="truncate text-sm text-gray-700">{item.title}</p>
                  </Link>
                )}
                
                {/* 3-Dot Button Container */}
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

                  {/* POPUP MENU */}
                  {activeMenuId === item.session_id && (
                    <div className="absolute right-0 top-6 z-50 w-[200px] overflow-hidden rounded-md border border-gray-200 bg-white shadow-lg ring-1 ring-black ring-opacity-5">
                      
                      {/* Delete Button */}
                      <button
                        onClick={(e) => handleDeleteSession(e, item.session_id)}
                        className="flex h-[46px] w-full items-center gap-3 px-4 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M3 6h18"></path>
                          <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                          <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                        </svg>
                        <span>ลบ</span>
                      </button>

                      {/* Rename Button */}
                      <button
                        onClick={(e) => startRename(e, item)}
                        className="flex h-[46px] w-full items-center gap-3 px-4 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                      >
                         <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
                          <path d="m15 5 4 4"/>
                         </svg>
                        <span>เปลี่ยนชื่อ</span>
                      </button>

                      {/* Pin Button */}
                       <button
                        onClick={(e) => handlePin(e, item)}
                        className="flex h-[46px] w-full items-center gap-3 px-4 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                      >
                         <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <line x1="12" y1="17" x2="12" y2="22"></line>
                          <path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-.53 1.44l-2.38 1.84A2 2 0 0 0 5 15.24Z"></path>
                         </svg>
                        <span>{item.is_pinned ? "เลิกปักหมุด" : "ปักหมุด"}</span>
                      </button>

                    </div>
                  )}
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
            <Link href="/merger">
              <div
                className="cursor-pointer truncate flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 shrink-0" >
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" >
                  <path d="M10 2v3" /><path d="M14 2v3" /><path d="M15 11V6h3l2 3v11c0 1.1-.9 2-2 2H6c-1.1 0-2-.9-2-2V9l2-3h3v5c0 1.1.9 2 2 2h2c1.1 0 2-.9 2-2Z" /><path d="M10 18h4" />
                </svg>
                Merger
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