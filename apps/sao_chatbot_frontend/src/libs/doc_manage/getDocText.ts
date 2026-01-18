// app/merger/api/getDocText.ts

const BASE_URL = "http://127.0.0.1:8000/api/v1/merger";

export async function getDocText(docId: string): Promise<string> {
  const res = await fetch(`${BASE_URL}/doc/${docId}/text`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Text not found");
  }

  return res.text();
}
