import { getBaseUrl } from "../config";

export async function checkHasPdf(docId: string): Promise<boolean> {
  try {
    const res = await fetch(
      `${getBaseUrl()}/api/v1/merger/doc/${docId}/original`
    );
    return res.ok;
  } catch {
    return false;
  }
}

export function getDocOriginalUrl(docId: string): string {
  return `${getBaseUrl()}/api/v1/merger/doc/${docId}/original`;
}
