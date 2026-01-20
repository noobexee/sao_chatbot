import { getBaseUrl } from "../config";

export interface SaveDocTextPayload {
  content: string; 
  title: string;        
  valid_from: string;   
  type: string; 
  valid_until?: string;  
  version?: string;       
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
  form.append("valid_from", payload.valid_from);
  form.append("type", payload.type);
  if (payload.valid_until) {
    form.append("valid_until", payload.valid_until);
  }
  if (payload.version) {
    form.append("version", payload.version);
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
