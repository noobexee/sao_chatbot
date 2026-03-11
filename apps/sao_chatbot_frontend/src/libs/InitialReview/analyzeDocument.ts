import { getBaseUrl } from "../config";

export interface AnalyzeResponse {
    status: string;
    session_id?: string; 
    user_id?: string;    
    data?: any;
    message?: string;
}

export async function analyzeDocument(
    file: File,
    sessionId?: string | null
): Promise<AnalyzeResponse> {

    const baseUrl = getBaseUrl();
    const formData = new FormData();

    const token = localStorage.getItem("token");

    formData.append("file", file);

    if (sessionId) {
        formData.append("session_id", sessionId);
    }

    try {
        const response = await fetch(`${baseUrl}/api/v1/InitialReview/analyze`, {
            method: "POST",
            headers: {
                Authorization: `Bearer ${token}`,
            },
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`Analysis failed: ${response.statusText}`);
        }

        return await response.json();

    } catch (error) {
        console.error("API Error (analyzeDocument):", error);
        throw error;
    }
}