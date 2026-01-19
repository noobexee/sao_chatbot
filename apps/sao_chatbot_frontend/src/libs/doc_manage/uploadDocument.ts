import { getBaseUrl } from "../config";

export interface UploadPayload {
  type: string;
  title?: string;
  version?: string;
  valid_from?: string;  // DD-MM-YYYY or ISO (backend decides)
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
  payload: UploadPayload,
  signal?: AbortSignal
): Promise<UploadResponse> {
  const formData = new FormData();

  formData.append("type", payload.type);
  if (payload.title) formData.append("title", payload.title);
  if (payload.version) formData.append("version", payload.version);
  if (payload.valid_from) formData.append("valid_from", payload.valid_from);
  if (payload.valid_until) formData.append("valid_until", payload.valid_until);
  formData.append("file", payload.file);

  const res = await fetch(`${getBaseUrl()}/api/v1/merger/doc`, {
    method: "POST",
    body: formData,
    cache: "no-store",
    signal,
  });
  if (!res.ok) {
    let message = "Upload failed";
    try {
      const data = await res.json();
      message = data.detail ?? JSON.stringify(data);
    } catch {
      message = await res.text();
    }
    throw new Error(message);
  }
  return res.json();
}
