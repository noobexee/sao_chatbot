// app/merger/api/getDocOriginal.ts

const BASE_URL = "http://127.0.0.1:8000/api/v1/merger";

export async function checkHasPdf(docId: string): Promise<boolean> {
  try {
    const res = await fetch(
      `${BASE_URL}/doc/${docId}/original`
    );
    return res.ok;
  } catch {
    return false;
  }
}

export function getDocOriginalUrl(docId: string): string {
  return `${BASE_URL}/doc/${docId}/original`;
}
