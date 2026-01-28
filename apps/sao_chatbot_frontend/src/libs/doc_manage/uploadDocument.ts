import { getBaseUrl } from "../config";

export interface UploadPayload {
  doc_type: string;
  title?: string;
  announce_date: string;   // ISO or DD-MM-YYYY
  effective_date: string;  // ISO or DD-MM-YYYY
  is_first_version: boolean;
  version: number;

  main_file: File;         // mandatory PDF
  related_files?: File[];  // optional
}

export interface UploadResponse {
  id: string;
  title: string;
  version: number;
  related_form_id?: string[] | null;
}


export async function uploadDocument(
  payload: UploadPayload,
  signal?: AbortSignal
): Promise<UploadResponse> {

  if (!payload.main_file) {
    throw new Error("Main PDF file is required");
  }

  if (
    payload.main_file.type !== "application/pdf" &&
    !payload.main_file.name.toLowerCase().endsWith(".pdf")
  ) {
    throw new Error("Main file must be a PDF");
  }

  if (payload.related_files?.length) {
    for (const f of payload.related_files) {
      if (!f.name) {
        throw new Error("Invalid related file detected");
      }
    }
  }

  const formData = new FormData();
  formData.append("doc_type", payload.doc_type);

  if (payload.title?.trim()) {
    formData.append("title", payload.title.trim());
  }
  formData.append("announce_date", payload.announce_date);
  formData.append("effective_date", payload.effective_date);
  formData.append(
    "is_first_version",
    String(payload.is_first_version)
  );

  formData.append("main_file", payload.main_file);

  payload.related_files?.forEach((file) => {
    formData.append("related_files", file);
  });

  const res = await fetch(
    `${getBaseUrl()}/api/v1/merger/doc`,
    {
      method: "POST",
      body: formData,
      cache: "no-store",
      signal,
    }
  );

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
