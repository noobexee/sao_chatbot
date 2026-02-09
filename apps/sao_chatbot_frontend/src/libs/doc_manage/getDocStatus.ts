import { getBaseUrl } from "../config";


export interface DocStatusResponse {
  status: string;
  current_page?: number;
  total_pages?: number;
}

export async function getDocStatus(
  docId: string
): Promise<DocStatusResponse> {
  const res = await fetch(`${getBaseUrl()}/api/v1/merger/doc/${docId}/status`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Cannot fetch status");
  }

  return res.json();
}
