import { getBaseUrl } from "../config";

export interface RelatedFile {
  id: string;
  document_id: string;
  file_name: string;
  file_data: string;   // base64 encoded
}

export async function getRelatedDoc(docId: string): Promise<RelatedFile[]> {
  const res = await fetch(
    `${getBaseUrl()}/api/v1/merger/doc/${docId}/related`,
    { cache: "no-store" }
  );

  if (!res.ok) {
    throw new Error("Failed to fetch related documents");
  }

  return res.json();
}