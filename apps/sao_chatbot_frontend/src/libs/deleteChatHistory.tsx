export default async function deleteChatHistory(user_id: string, session_id: string) {
  const url = `http://localhost:8000/api/v1/sessions/${user_id}/${session_id}`;
  
  try {
    const response = await fetch(url, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      return { 
        success: false, 
        message: errorData?.message || `Error: ${response.status} ${response.statusText}`,
        data: null
      };
    }

    return await response.json();
    
  } catch (error) {
    console.error("Failed to delete session:", error);
    return { 
      success: false, 
      message: "Network error or server unreachable", 
      data: null 
    };
  }
}