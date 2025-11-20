import getChatHistory from "@/libs/getChatHistory";
import ChatWindow from "@/components/ChatWindow";

// 1. Define params as a Promise (Required for Next.js 15)
interface PageProps {
  params: Promise<{
    sessionId: string; 
  }>;
}

export default async function SpecificChatPage({ params }: PageProps) {
  const userId = "1";

  const { sessionId } = await params;
  const historyData = await getChatHistory(userId, sessionId);
  const messages = historyData?.data?.messages || [];

  return (
    <ChatWindow 
      initialMessages={messages} 
      sessionId={sessionId} 
      userId={userId} 
    />
  );
}