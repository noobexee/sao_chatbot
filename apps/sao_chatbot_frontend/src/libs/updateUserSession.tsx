export async function updateSession(
  userId: string, 
  sessionId: string, 
  updates: { title?: string; is_pinned?: boolean }
) {
  const url = `${process.env.NEXT_PUBLIC_RAG_API_URL}/api/v1/chatbot/sessions/${userId}/${sessionId}`;
  
  try {
    const response = await fetch(url, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });

    if (!response.ok) {
        const err = await response.json().catch(() => null);
        return { 
          success: false, 
          message: err?.message || `Request failed with status ${response.status}`, 
          data: null 
        };
    }
    return await response.json();
  } catch (error) {
    console.error("Update Session Error:", error);
    return { success: false, message: "Network Error or Server Unreachable", data: null };
  }
}