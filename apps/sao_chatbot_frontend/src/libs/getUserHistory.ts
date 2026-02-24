import { getBaseUrl } from "./config";

export default async function getUserHistory() {
  const baseUrl = getBaseUrl();
  const token = localStorage.getItem("token");

  if (!token) {
    throw new Error("Not authenticated");
  }

  const response = await fetch(`${baseUrl}/api/v1/chatbot/sessions`, {
    cache: "no-store",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  
  if (!response.ok) {
    throw new Error("Failed to fetch history");
  }

  return await response.json();
}