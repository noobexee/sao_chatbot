"use client";

import { use, useEffect, useState } from "react";
import getChatHistory from "@/libs/getChatHistory";
import ChatWindow from "@/components/ChatWindow";

interface PageProps {
  params: Promise<{
    sessionId: string;
  }>;
}

export default function SpecificChatPage({ params }: PageProps) {
  const { sessionId } = use(params);

  const [messages, setMessages] = useState<any[]>([]);

  function parseJwt(token: string) {
    try {
      const base64 = token.split(".")[1];
      return JSON.parse(atob(base64));
    } catch {
      return null;
    }
  }

  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token) {
      throw new Error("Unauthorized");
    }

    const payload = parseJwt(token);
    const uid = payload?.sub;

    if (!uid) {
      throw new Error("Invalid token");
    }

    const fetchData = async () => {
      const historyData = await getChatHistory(sessionId);
      const msgs = historyData?.data?.messages || [];
      setMessages(msgs);
    };

    fetchData();
  }, [sessionId]);

  return (
    <ChatWindow
      initialMessages={messages}
      sessionId={sessionId}
    />
  );
}