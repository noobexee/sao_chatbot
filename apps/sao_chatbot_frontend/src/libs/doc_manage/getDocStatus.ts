// libs/doc_manage/getDocStatus.ts

const BASE_URL = "http://127.0.0.1:8000/api/v1/merger";

export type DocStatus = "queued" | "processing" | "done" | "error";

export interface DocStatusResponse {
  status: DocStatus;
  current_page?: number;
  total_pages?: number;
  message?: string;
}

export async function getDocStatus(
  docId: string
): Promise<DocStatusResponse> {
  const res = await fetch(`${BASE_URL}/doc/${docId}/status`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Cannot fetch status");
  }

  return res.json();
}
