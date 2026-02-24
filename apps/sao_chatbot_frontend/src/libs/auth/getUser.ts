import { getBaseUrl } from "../config";

export async function getAllUsers(token: string) {
  const res = await fetch(`${getBaseUrl()}/api/v1/auth/users`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Failed to fetch users");
  }

  return res.json();
}