import { getBaseUrl } from "../config";

export type MergePreference = "edit_context" | "replace_all";

export async function updateSnapshot(
  base_doc_id: string,
  amend_doc_id: string,
  merge_mode: MergePreference = "edit_context"
) {
  const res = await fetch(`${getBaseUrl()}/api/v1/merger/merge`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      base_doc_id,
      amend_doc_id,
      merge_mode, // ✅ new
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Merge failed");
  }

  return res.json();
}
