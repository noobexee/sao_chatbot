export default async function getChatHistory(user_id: string, session_id: string) {
  const url = `${process.env.NEXT_PUBLIC_RAG_API_URL}/api/v1/chatbot/history/${user_id}/${session_id}`;
  
  console.log(`Fetching history from: ${url}`);

  const response = await fetch(url, {
    cache: "no-store",
  });

  if (!response.ok) {
   
    return { success: true, data: { messages: [] } };
  }

  return await response.json();
}