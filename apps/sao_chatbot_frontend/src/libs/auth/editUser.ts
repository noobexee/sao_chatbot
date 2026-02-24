import { getBaseUrl } from "../config";

export async function updateUser(
  userId: string,
  username: string,
  password: string,
  role: string,
  token: string
) {
  const res = await fetch(
    `${getBaseUrl()}/api/v1/auth/users/${userId}?username=${username}&password=${password}&role=${role}`,
    {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    }
  );

  if (!res.ok) {
    throw new Error("Failed to update user");
  }

  return res.json();
}