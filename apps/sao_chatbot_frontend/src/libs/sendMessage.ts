import { getBaseUrl } from "./config";

export default async function sendMessage(
  sessionId: string,
  message: string
) {
  const baseUrl = getBaseUrl();
  const token = localStorage.getItem("token");

  try {
    const response = await fetch(`${baseUrl}/api/v1/chatbot/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`, 
      },
      body: JSON.stringify({
        session_id: sessionId, 
        query: message,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => null);
      throw new Error(err?.message || `HTTP error! status: ${response.status}`);
    }

    const resJson = await response.json();
    return resJson.data;

  } catch (error) {
    console.error("Failed to send message:", error);
    throw error;
  }
}