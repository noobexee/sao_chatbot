import { getBaseUrl } from "../config";

export interface SaveDocTextPayload {
  content: string;
  title: string;          // DocumentMeta.title
  type: string;           // DocumentMeta.type
  announce_date: string;  // ISO or DD-MM-YYYY
  effective_date?: string; // ISO or DD-MM-YYYY (optional)
}

export async function saveDocText(
  docId: string,
  payload: SaveDocTextPayload
): Promise<void> {
  const form = new FormData();

  const file = new File(
    [payload.content],
    "text.txt",
    { type: "text/plain" }
  );

  form.append("file", file);
  form.append("title", payload.title);
  form.append("type", payload.type);
  form.append("announce_date", payload.announce_date);

  if (payload.effective_date) {
    form.append("effective_date", payload.effective_date);
  }

  const res = await fetch(
    `${getBaseUrl()}/api/v1/merger/doc/${docId}/edit`,
    {
      method: "PUT",
      body: form,
      cache: "no-store",
    }
  );

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Failed to update document");
  }
}
