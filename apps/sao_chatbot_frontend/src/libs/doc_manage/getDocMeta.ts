import { getBaseUrl } from "../config";

export interface DocMeta {
  title: string;
  type: string;
  valid_from: string;          // ISO date string (YYYY-MM-DD)
  valid_until?: string; // optional date
  version: string;
  is_snapshot?: boolean;
  got_updated?: boolean;
  is_first_version?: boolean;
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
