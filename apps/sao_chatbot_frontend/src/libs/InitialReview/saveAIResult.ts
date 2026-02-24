import { getBaseUrl } from "../config";

export interface SaveResultPayload {
    InitialReview_id: string;
    criteria_id: number;
    result: any; // The structured data from the criteria
}

export interface SaveResultResponse {
    status: string;
    message: string;
}

export async function saveAiResult(payload: SaveResultPayload): Promise<SaveResultResponse> {
    const baseUrl = getBaseUrl();
    try {
        const response = await fetch(`${baseUrl}/api/v1/InitialReview/save_result`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            throw new Error(`Failed to save result: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error("API Error (saveAiResult):", error);
        throw error;
    }
}