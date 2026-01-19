import { getBaseUrl } from "../config";

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

export async function getDocuments(): Promise<Doc[]> {
  const res = await fetch(`${getBaseUrl()}/api/v1/merger/doc`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Failed to fetch documents");
  }

  return res.json();
}
