// app/merger/api/getDocMeta.ts

export interface DocMeta {
  title: string;
  type: string;
  version: string;
  valid_from: string;
  valid_until: string | null;
}

const BASE_URL = "http://127.0.0.1:8000/api/v1/merger";

export async function getDocMeta(docId: string): Promise<DocMeta> {
  const res = await fetch(`${BASE_URL}/doc/${docId}/meta`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Failed to fetch document meta");
  }

  return res.json();
}
