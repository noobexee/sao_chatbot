"use client"; 

import React, { useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation"; 
import { v4 as uuidv4 } from "uuid"; 
import sendMessage from "@/libs/sendMessage";

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  function parseJwt(token: string) {
    try {
      const base64 = token.split(".")[1];
      return JSON.parse(atob(base64));
    } catch {
      return null;
    }
  }

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const token = localStorage.getItem("token");

    if (!token) {
      alert("Unauthorized");
      return;
    }

    const payload = parseJwt(token);
    const userId = payload?.sub;

    if (!userId) {
      alert("Invalid token");
      return;
    }

    const userText = input;
    const newSessionId = uuidv4();
    setIsLoading(true);

    try {
      await sendMessage(newSessionId, userText);

      router.push(`/chatbot/${newSessionId}`);
      window.dispatchEvent(new Event("session-updated"));
      
    } catch (error) {
      console.error("Failed to start chat:", error);
      setIsLoading(false);
      alert("Failed to send message. Please try again.");
    }
  };

  return (
    <div className="flex h-full flex-col items-center justify-center px-4">
        
        <div className="mb-6">
          <Image
            src="/logo.png"
            alt="SAO Logo"
            width={1200}
            height={1200}
            className="h-auto w-32 md:w-40 drop-shadow-sm"
            priority
          />
        </div>

        <h2 className="mb-10 text-xl font-bold text-[#1e293b] md:text-2xl">
          SAO chatbot as assistance
        </h2>

        <div className="w-full max-w-3xl">
          <form 
            onSubmit={handleSend}
            className="relative flex items-center rounded-[2rem] border border-gray-200 bg-white py-2 pl-6 pr-2 shadow-[0_2px_8px_rgba(0,0,0,0.05)] transition-shadow focus-within:shadow-[0_4px_12px_rgba(0,0,0,0.08)]"
          >
            
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="ส่งข้อความให้ SAO bot"
              className="flex-1 border-none bg-transparent text-base text-gray-700 placeholder-gray-400 outline-none focus:ring-0"
              disabled={isLoading}
            />

            <button 
              type="submit"
              disabled={!input.trim() || isLoading}
              className="cursor-pointer truncate flex h-10 w-10 items-center justify-center rounded-full bg-[#a83b3b] text-white transition-colors hover:bg-[#8f3232] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>
                </svg>
              )}
            </button>

          </form>
        </div>
    </div>
  );
}