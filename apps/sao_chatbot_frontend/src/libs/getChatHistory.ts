import { getBaseUrl } from "./config";

export default async function getChatHistory(session_id: string) {
  const baseUrl = getBaseUrl();
  const token = localStorage.getItem("token");

  const url = `${baseUrl}/api/v1/chatbot/history/${session_id}`;

  const response = await fetch(url, {
    cache: "no-store",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  
  if (!response.ok) {
    return { success: true, data: { messages: [] } };
  }

  return await response.json();
}