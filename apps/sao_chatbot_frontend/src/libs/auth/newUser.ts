import { getBaseUrl } from "../config";

export async function createUser(
  username: string,
  password: string,
  role: string,
  token: string
) {
  const res = await fetch(
    `${getBaseUrl()}/api/v1/auth/users?username=${username}&password=${password}&role=${role}`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    }
  );

  if (!res.ok) {
    throw new Error("Failed to create user");
  }

  return res.json();
}