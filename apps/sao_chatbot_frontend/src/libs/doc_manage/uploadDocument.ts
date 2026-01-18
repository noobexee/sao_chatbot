// app/merger/api/uploadDocument.ts

const BASE_URL = "http://127.0.0.1:8000/api/v1/merger";

export interface UploadPayload {
  type: string;
  title?: string;
  version?: string;
  valid_from?: string;
  valid_until?: string;
  file: File;
}

export interface UploadResponse {
  id: string;
  type: string;
  title: string;
  version: string | null;
  message: string;
  status_endpoint: string;
  text_endpoint: string;
}

export async function uploadDocument(
  payload: UploadPayload
): Promise<UploadResponse> {
  const formData = new FormData();

  formData.append("type", payload.type);
  if (payload.title) formData.append("title", payload.title);
  if (payload.version) formData.append("version", payload.version);
  if (payload.valid_from) formData.append("valid_from", payload.valid_from);
  if (payload.valid_until) formData.append("valid_until", payload.valid_until);
  formData.append("file", payload.file);

  const res = await fetch(`${BASE_URL}/doc`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || "Upload failed");
  }

  return res.json();
}
