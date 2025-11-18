"use client";

import React, { useState, useEffect, useRef } from "react";
import Image from "next/image";
import Link from "next/link";

// Mock chat history data 
const initialHistory = [
  { id: "1", title: "การคัดเลือกเรื่องที่มาจากการประเมินความเสี่ยง..." },
  { id: "2", title: "เรื่องที่มาจากการร้องเรียนมีกี่ประเภท อะไรบ้าง" },
  { id: "3", title: "เรื่องที่สำนักงานจะรับไว้ตรวจสอบการปฏิบัติตาม..." },
  { id: "4", title: "การประทับตราชั้นความลับของรายงาน ต้องดำเนิน..." },
  { id: "5", title: "หลักเกณฑ์การพิจารณารับเรื่องร้องเรียน มีอะไรบ้..." },
];

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // 1. State for managing the list (allows deletion)
  const [history, setHistory] = useState(initialHistory);
  
  // 2. State to track which menu is open (by ID)
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);

  // Function to toggle the specific menu
  const toggleMenu = (e: React.MouseEvent, id: string) => {
    e.preventDefault(); // Prevent Link navigation when clicking dots
    e.stopPropagation();
    if (activeMenuId === id) {
      setActiveMenuId(null); // Close if already open
    } else {
      setActiveMenuId(id); // Open this one
    }
  };

  // Function to Delete
  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    // Filter out the item with this ID
    setHistory((prev) => prev.filter((item) => item.id !== id));
    setActiveMenuId(null); // Close menu
  };

  // Function to Close menu when clicking anywhere else
  useEffect(() => {
    const closeMenu = () => setActiveMenuId(null);
    document.addEventListener("click", closeMenu);
    return () => document.removeEventListener("click", closeMenu);
  }, []);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-white text-[#1e293b]">
      <aside 
        className={`
          flex flex-col border-r border-gray-100 bg-[#f8f9fa] shrink-0 transition-all duration-300 ease-in-out overflow-hidden
          ${isSidebarOpen ? "w-[280px]" : "w-0 border-none"}
        `}
      >
        
        <div className="flex items-center justify-between p-5 pb-2 whitespace-nowrap">
          <h1 className="text-xl font-bold text-[#1e293b]">SAO Chatbot</h1>
          <button className="cursor-pointer truncate text-gray-600 hover:text-black">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
            </svg>
          </button>
        </div>

        <div className="px-2 py-2 whitespace-nowrap">
          <Link href="/chatbot">
            <button className="cursor-pointer truncate flex w-full items-center gap-3 rounded-md bg-[#e2e4e6] px-4 py-3 text-left transition-colors hover:bg-gray-300">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" className="text-[#333]">
                <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
              </svg>
              <span className="font-bold text-[#a83b3b]">แชทใหม่</span>
            </button>
          </Link>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4 whitespace-nowrap">
          <h2 className="mb-3 text-sm font-bold text-[#1e293b]">ล่าสุด</h2>
          <div className="space-y-4 text-sm text-gray-600">
            {history.map((item) => (
              <Link key={item.id} href={`/chatbot/${item.id}`}>
                <div className="flex items-center justify-between group cursor-pointer rounded-md p-2 -mx-2 hover:bg-gray-200 transition-colors">
                  <p className="truncate group-hover:text-black">{item.title}</p>
                  <button className="opacity-0 group-hover:opacity-100 p-1 rounded-full hover:bg-gray-300 transition-opacity">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-500">
                      <circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>
                    </svg>
                  </button>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </aside>

      <main className="flex flex-1 flex-col relative h-full gap-30">
        <header className="flex h-16 w-full items-center justify-between border-b border-gray-100 bg-white px-4 shrink-0 z-50">
          <div className="absolute top-4 right-6 flex items-center gap-3 z-50">
            <button 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="cursor-pointer truncate flex h-10 w-10 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" x2="21" y1="6" y2="6"/><line x1="3" x2="21" y1="12" y2="12"/><line x1="3" x2="21" y1="18" y2="18"/>
              </svg>
            </button>
            
            <div className="cursor-pointer truncate relative h-10 w-10 overflow-hidden rounded-full border border-gray-200 bg-gray-200">
              <Image 
                src="/user-placeholder.jpg" 
                alt="User"
                fill
                className="object-cover"
              />
              <span className="absolute bottom-0 right-0 block h-3 w-3 rounded-full bg-green-500 ring-2 ring-white"></span>
            </div>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}