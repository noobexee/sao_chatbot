export default async function sendMessage(userId: string, sessionId: string, message: string) {
  try {
    const response = await fetch("http://127.0.0.1:8000/api/v1/query", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        // Backend expects integer for user_id, ensuring conversion
        user_id: parseInt(userId),
        session_id: sessionId,
        query: message,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const resJson = await response.json();
    
    // Our API returns { success: true, data: { answer: "...", ... } }
    return resJson.data; 

  } catch (error) {
    console.error("Failed to send message:", error);
    throw error;
  }
}