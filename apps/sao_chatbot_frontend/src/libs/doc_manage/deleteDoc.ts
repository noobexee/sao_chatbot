import { getBaseUrl } from "../config";

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${getBaseUrl()}/api/v1/merger/doc/${docId}`, {
    method: "DELETE",
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to delete document: ${text}`);
  }
}
