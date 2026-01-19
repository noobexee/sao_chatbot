import { getBaseUrl } from "../config";

export interface SaveSessionPayload {
    audit_id: string;
    file_name: string;
}

export interface SaveSessionResponse {
    status: string;
    audit_id: string;
    message?: string;
}

export async function saveAuditSession(payload: SaveSessionPayload): Promise<SaveSessionResponse> {
    const baseUrl = getBaseUrl();
    try {
        // Pointing to legacy endpoint as it wasn't in V1 controller
        const response = await fetch(`${baseUrl}/save_audit`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            throw new Error(`Failed to save session: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error("API Error (saveAuditSession):", error);
        throw error;
    }
}