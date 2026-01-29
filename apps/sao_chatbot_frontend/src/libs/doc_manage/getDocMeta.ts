import { getBaseUrl } from "../config";

export interface DocMeta {
  title: string;                 // law_name
  type: string;                  // doc_type
  announce_date: string;         // ISO date (YYYY-MM-DD)
  effective_date: string;        // ISO date (YYYY-MM-DD)
  version: number | null;        // 1 for first version, +1 per amendment
  is_snapshot: boolean;          // generated from merge (no pdf)
  is_latest: boolean;            // latest version flag
  related_form_id: string[] | null; // related uploaded forms
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
