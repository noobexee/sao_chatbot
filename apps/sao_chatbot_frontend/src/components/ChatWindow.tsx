"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import Image from "next/image";
import Link from "next/link";
import ReactMarkdown from "react-markdown"; 
import { useRouter } from "next/navigation";
import sendMessage from "@/libs/chatbot/sendMessage";

interface Reference {
  name: string;
  doc_id: string;
}

interface Message {
  role: string;
  content: string;
  created_at: string;
  references?: Reference[]; 
}

interface ChatWindowProps {
  initialMessages: any[];  
  sessionId: string;
}

export default function ChatWindow({ initialMessages, sessionId }: ChatWindowProps) {
  
  const formatMessages = (msgs: any[]): Message[] => {
    return msgs.map((msg) => {
      let parsedReferences: Reference[] = [];

      if (msg.references) {
        if (Array.isArray(msg.references)) {
          parsedReferences = msg.references;
        } else if (typeof msg.references === "object") {
          parsedReferences = Object.entries(msg.references).map(([key, value]) => ({
            name: key,
            doc_id: value as string,
          }));
        }
      }

      return {
        role: msg.role,
        content: msg.content,
        created_at: msg.created_at,
        references: parsedReferences.length > 0 ? parsedReferences : undefined,
      };
    });
  };

  const [messages, setMessages] = useState<Message[]>(() => formatMessages(initialMessages));
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const router = useRouter();

  useEffect(() => {
    setTimeout(() => {
      scrollRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 50);
  }, [messages, isLoading]);

  useEffect(() => {
    setMessages(formatMessages(initialMessages));
  }, [initialMessages]);
  
  const formatTime = (dateString: string) => {
    if (!dateString) return "";
    const date = new Date(dateString);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // Auto-resize textarea as content grows
  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto"; // reset to shrink when text is deleted
      el.style.height = `${el.scrollHeight}px`;
    }
  }, []);

  // Enter → send, Shift+Enter → newline
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const userText = input;
    setInput("");

    // Reset textarea height after clearing
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    const newMessage: Message = {
      role: "user",
      content: userText,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, newMessage]);
    setIsLoading(true);

    try {
      const responseData = await sendMessage(sessionId, userText);
      
      const answerText = responseData.data ? responseData.data.answer : responseData.answer;
      const refObject = responseData.data ? responseData.data.ref : responseData.ref;
      
      const lawReferences: Reference[] = refObject 
        ? Object.entries(refObject).map(([key, value]) => ({
            name: key,
            doc_id: value as string
          })) 
        : [];
      
      const aiMessage: Message = {
        role: "assistant",
        content: answerText || "ไม่พบข้อความตอบกลับ",
        created_at: new Date().toISOString(),
        references: lawReferences,
      };
      
      setMessages((prev) => [...prev, aiMessage]);
      router.refresh();

    } catch (error) {
      console.error(error);
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
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    ) : (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    )}
                  </div>

                  {!isUser && msg.references && msg.references.length > 0 && (
                    <div className="mt-3 flex flex-col gap-1.5">
                      <p className="text-xs font-semibold text-gray-500 mb-1">อ้างอิงจาก:</p>
                      <div className="flex flex-wrap gap-2">
                        {msg.references.map((law, i) => (
                          <Link 
                            key={i} 
                            href={`/merger/${law.doc_id}/view`}
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-xs bg-blue-50 text-blue-700 hover:bg-blue-100 hover:text-blue-800 px-3 py-1.5 rounded-md border border-blue-200 shadow-sm transition-colors cursor-pointer flex items-center gap-1"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                            </svg>
                            {law.name}
                          </Link>
                        ))}
                      </div>
                    </div>
                  )}
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
            className="relative flex items-end rounded-[2rem] border border-gray-200 bg-white py-2 pl-6 pr-2 shadow-[0_2px_8px_rgba(0,0,0,0.05)] transition-shadow focus-within:shadow-[0_4px_12px_rgba(0,0,0,0.08)]"
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="ส่งข้อความให้ SAO bot"
              rows={1}
              className="flex-1 resize-none overflow-hidden border-none bg-transparent text-base text-gray-700 placeholder-gray-400 outline-none focus:ring-0 py-2 leading-6 max-h-48 overflow-y-auto"
              disabled={isLoading}
            />

            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="mb-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#a83b3b] text-white transition-colors hover:bg-[#8f3232] disabled:opacity-50 disabled:cursor-not-allowed"
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
