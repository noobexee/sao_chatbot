import { getBaseUrl } from "../config";

export async function updateSnapshot(
  base_doc_id: string,
  amend_doc_id: string
) {
  const res = await fetch(`${getBaseUrl()}/api/v1/merger/merge`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      base_doc_id,
      amend_doc_id,
    }),
  });

  if (!res.ok) {
    throw new Error("Merge failed");
  }

  return res.json(); 
}

