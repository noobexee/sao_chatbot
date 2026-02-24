import { getBaseUrl } from "../config";

export interface SaveSessionPayload {
    InitialReview_id: string;
    file_name: string;
}

export interface SaveSessionResponse {
    status: string;
    InitialReview_id: string;
    message?: string;
}

export async function saveInitialReviewSession(payload: SaveSessionPayload): Promise<SaveSessionResponse> {
    const baseUrl = getBaseUrl();
    try {
        // Pointing to legacy endpoint as it wasn't in V1 controller
        const response = await fetch(`${baseUrl}/save_InitialReview`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            throw new Error(`Failed to save session: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error("API Error (saveInitialReviewSession):", error);
        throw error;
    }
}