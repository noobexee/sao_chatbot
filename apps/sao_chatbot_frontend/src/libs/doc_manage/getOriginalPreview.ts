import { getBaseUrl } from "../config";

export type PreviewFile = {
  type: "pdf";
  previewUrl: string;
};

export async function getDocOriginalPreview(
  docId: string
): Promise<PreviewFile> {
  const res = await fetch(`${getBaseUrl()}/api/v1/merger/doc/${docId}/original`, {
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
