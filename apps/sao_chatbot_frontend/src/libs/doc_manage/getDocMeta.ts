import { getBaseUrl } from "../config";

export interface DocMeta {
  title: string;
  type: string;
  announce_date: string;   // ISO date (YYYY-MM-DD)
  effective_date: string;  // ISO date (YYYY-MM-DD)
  version: string | null;
  is_snapshot: boolean;
  is_latest: boolean;
  is_first_version: boolean;
}


export async function getDocMeta(docId: string): Promise<DocMeta> {
  const res = await fetch(
    `${getBaseUrl()}/api/v1/merger/doc/${docId}/meta`,
    { cache: "no-store" }
  );

  if (!res.ok) {
    throw new Error("Failed to fetch document meta");
  }

  return res.json();
}
