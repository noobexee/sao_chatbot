import { getBaseUrl } from "../config";

export async function deleteUser(
  userId: string,
  token: string
) {
  const res = await fetch(
    `${getBaseUrl()}/api/v1/auth/users/${userId}`,
    {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    }
  );

  if (!res.ok) {
    throw new Error("Failed to delete user");
  }

  return res.json();
}