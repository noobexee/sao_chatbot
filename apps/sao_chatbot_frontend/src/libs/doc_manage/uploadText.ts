const BASE_URL = "http://127.0.0.1:8000/api/v1/merger";

export async function saveDocText(
  docId: string,
  content: string
): Promise<void> {
  const form = new FormData();
  const blob = new Blob([content], { type: "text/plain" });
  form.append("file", blob, "text.txt");

  const res = await fetch(`${BASE_URL}/doc/${docId}/text`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    throw new Error("Failed to save cleaned text");
  }
}
