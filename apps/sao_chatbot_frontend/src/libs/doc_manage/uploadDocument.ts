import { getBaseUrl } from "../config";

export interface UploadPayload {
  type: string;
  title?: string;
  version?: string;
  announce_date: string;   // ISO or DD-MM-YYYY
  effective_date: string;  // ISO or DD-MM-YYYY
  is_first_version: boolean;
  file: File;
}

export interface UploadResponse {
  id: string;
  type: string;
  title: string;
  version: string | null;
  is_snapshot: boolean;
}

export async function uploadDocument(
  payload: UploadPayload,
  signal?: AbortSignal
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("type", payload.type);
  if (payload.title) formData.append("title", payload.title);
  if (payload.version) formData.append("version", payload.version);
  formData.append("announce_date", payload.announce_date);
  formData.append("effective_date", payload.effective_date);
  formData.append(
    "is_first_version",
    String(payload.is_first_version)
  );

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
