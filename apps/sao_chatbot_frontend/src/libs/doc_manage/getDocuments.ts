import { getBaseUrl } from "../config";


export interface Doc {
  id: string;
  title: string;
  type: string;
  version: string | null;
  announce_date: string;   // ISO date
  effective_date: string;  // ISO date
  is_snapshot: boolean;
  is_latest: boolean;
  is_first_version: boolean;
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
