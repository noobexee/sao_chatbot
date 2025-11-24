"use client";

import React, { useState, useEffect, useRef } from "react";
import Image from "next/image";
import ReactMarkdown from "react-markdown"; 
import { useRouter } from "next/navigation";
import sendMessage from "@/libs/sendMessage";

interface Message {
  role: string;
  content: string;
  created_at: string;
}

interface ChatWindowProps {
  initialMessages: Message[];
  sessionId: string;
  userId: string;
}

export default function ChatWindow({ initialMessages, sessionId, userId }: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const formatTime = (dateString: string) => {
    if (!dateString) return "";
    const date = new Date(dateString);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const userText = input;
    setInput(""); 

    const newMessage: Message = {
      role: "user",
      content: userText,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, newMessage]);
    setIsLoading(true);

    try {
      const responseData = await sendMessage(userId, sessionId, userText);
      
      const aiMessage: Message = {
        role: "assistant",
        content: responseData.answer,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, aiMessage]);
      
      router.refresh();

    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "❌ Error connecting to server.", created_at: new Date().toISOString() },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative flex h-full flex-col bg-white">
      <div className="flex-1 overflow-y-auto scroll-smooth p-4 pb-24">
        <div className="mx-auto max-w-3xl space-y-6">
          
          {messages.length === 0 && (
             <div className="text-center text-gray-400 mt-10">เริ่มการสนทนาใหม่กับ SAO Bot</div>
          )}

          {messages.map((msg, idx) => {
            const isUser = msg.role === "user";
            return (
              <div key={idx} className="flex w-full gap-3 items-start">

                <div className={`h-8 w-8 shrink-0 flex items-center justify-center rounded-full border border-gray-100 overflow-hidden ${isUser ? "bg-gray-200" : "bg-[#a83b3b] text-white"}`}>
                  {isUser ? (
                    <Image src="/user-placeholder.jpg" alt="User" width={32} height={32} className="object-cover" />
                  ) : (
                    <span className="text-xs font-semibold">SAO</span>
                  )}
                </div>

                <div className="flex flex-col w-full min-w-0">
                  <div className="flex items-baseline gap-2 mb-1">
                    <span className="font-semibold text-sm">{isUser ? "คุณ" : "SAO bot"}</span>
                    <span className="text-xs text-gray-500">{formatTime(msg.created_at)}</span>
                  </div>
                  
                  <div className={`leading-relaxed text-gray-800 break-words ${!isUser ? "prose prose-sm max-w-none" : ""}`}>
                    {isUser ? (
                       <p>{msg.content}</p>
                    ) : (
                       <ReactMarkdown>{msg.content}</ReactMarkdown>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {isLoading && (
            <div className="flex w-full gap-3 items-start opacity-70">
              <div className="h-8 w-8 shrink-0 flex items-center justify-center rounded-full bg-[#a83b3b] text-white text-xs font-semibold">SAO</div>
              <div className="flex flex-col">
                 <span className="font-semibold text-sm mb-1">SAO bot</span>
                 <div className="flex gap-1 h-6 items-center">
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-75"></span>
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-150"></span>
                 </div>
              </div>
            </div>
          )}
          
          <div ref={scrollRef} />
        </div>
      </div>

      <div className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-white via-white to-transparent pt-10 pb-6">
        <div className="mx-auto max-w-3xl px-4">
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
              className="flex h-10 w-10 items-center justify-center rounded-full bg-[#a83b3b] text-white transition-colors hover:bg-[#8f3232] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>
              </svg>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}