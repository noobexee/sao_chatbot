import { getBaseUrl } from "../config";

export async function getDocText(docId: string): Promise<string> {
  const res = await fetch(`${getBaseUrl()}/api/v1/merger/doc/${docId}/text`, {
    method: "GET",
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Text not found");
  }

  return res.text();
}
