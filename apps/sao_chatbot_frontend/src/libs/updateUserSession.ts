import { getBaseUrl } from "./config";

export async function updateSession(
  sessionId: string,
  updates: { title?: string; is_pinned?: boolean }
) {
  const baseUrl = getBaseUrl();

  // ✅ ตัด userId ออก
  const url = `${baseUrl}/api/v1/chatbot/sessions/${sessionId}`;

  try {
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("token")
        : null;

    if (!token) {
      return {
        success: false,
        message: "No token found",
        data: null,
      };
    }

    const response = await fetch(url, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`, // ✅ สำคัญ
      },
      body: JSON.stringify(updates),
      cache: "no-store",
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      return {
        success: false,
        message: data?.message || `Error: ${response.status}`,
        data: null,
      };
    }

    return {
      success: true,
      message: "Session updated successfully",
      data,
    };
  } catch (error) {
    console.error("Update Session Error:", error);
    return {
      success: false,
      message: "Network error or server unreachable",
      data: null,
    };
  }
}