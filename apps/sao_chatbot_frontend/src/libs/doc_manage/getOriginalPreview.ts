const BASE_URL = "http://127.0.0.1:8000/api/v1/merger";

export type PreviewFile = {
  type: "pdf";
  previewUrl: string;
};

export async function getDocOriginalPreview(
  docId: string
): Promise<PreviewFile> {
  const res = await fetch(`${BASE_URL}/doc/${docId}/original`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Cannot load PDF");
  }

  const blob = await res.blob();
  const previewUrl = URL.createObjectURL(blob);

  return {
    type: "pdf",
    previewUrl,
  };
}
