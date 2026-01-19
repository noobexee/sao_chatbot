import { getBaseUrl } from "../config";

export interface SaveDocTextPayload {
  content: string;
  title?: string;
  valid_from?: string; 
  valid_until?: string;
  version?: string;
}

export async function saveDocText(
  docId: string,
  payload: SaveDocTextPayload
): Promise<void> {
  const form = new FormData();
  const blob = new Blob([payload.content], { type: "text/plain" });
  form.append("file", blob, "text.txt");
  if (payload.title !== undefined) {
    form.append("title", payload.title);
  }
  if (payload.valid_from !== undefined) {
    form.append("valid_from", payload.valid_from);
  }
  if (payload.valid_until !== undefined) {
    form.append("valid_until", payload.valid_until);
  }
  if (payload.version !== undefined) {
    form.append("version", payload.version);
  }
  const res = await fetch(
    `${getBaseUrl()}/api/v1/merger/doc/${docId}/text`,
    {
      method: "PUT",
      body: form,
      cache: "no-store",
    }
  );
  if (!res.ok) {
    let message = "Failed to save cleaned text";
    try {
      const data = await res.json();
      message = data.detail ?? JSON.stringify(data);
    } catch {
      message = await res.text();
    }
    throw new Error(message);
  }
}
