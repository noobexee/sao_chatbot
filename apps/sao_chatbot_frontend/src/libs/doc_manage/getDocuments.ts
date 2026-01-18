export interface Doc {
  id: string;
  title: string;
  type: string;
  version: string;
  valid_from: string;
  valid_until: string | null;
  has_pdf: boolean;
  has_text: boolean;
  status: string;
}

const BASE_URL = "http://127.0.0.1:8000/api/v1/merger";

export async function getDocuments(): Promise<Doc[]> {
  const res = await fetch(`${BASE_URL}/doc`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Failed to fetch documents");
  }

  return res.json();
}
