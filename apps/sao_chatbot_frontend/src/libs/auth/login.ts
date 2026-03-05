import { getBaseUrl } from "../config";

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    username: string;
    role: string;
  };
}

export async function login(
  username: string,
  password: string
): Promise<LoginResponse> {
  const res = await fetch(
    `${getBaseUrl()}/api/v1/auth/login`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        username,
        password,
      }),
    }
  );

  if (!res.ok) {
    throw new Error("Invalid username or password");
  }

  return res.json();
}