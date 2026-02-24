import { getBaseUrl } from "./config";

export default async function deleteChatHistory(session_id: string) {
  const baseUrl = getBaseUrl();
  const token = localStorage.getItem("token");

  const url = `${baseUrl}/api/v1/chatbot/sessions/${session_id}`;

  try {
    const response = await fetch(url, {
      method: "DELETE",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`, 
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);

      return {
        success: false,
        message:
          errorData?.message ||
          `Error: ${response.status} ${response.statusText}`,
        data: null,
      };
    }

    return await response.json();

  } catch (error) {
    console.error("Failed to delete session:", error);

    return {
      success: false,
      message: "Network error or server unreachable",
      data: null,
    };
  }
}