import { getBaseUrl } from "../config";

export interface AnalyzeResponse {
    status: string;
    session_id?: string;
    user_id?: string;
    data: {
        criteria1: any;
        criteria2: any; 
        criteria4: any; 
        criteria6: any;
        criteria8: any;
        raw_text?: string;
    };
    message?: string;
}

export async function analyzeDocument(file: File, user_id: string, session_id?: string): Promise<AnalyzeResponse> {
    const baseUrl = getBaseUrl();
    const formData = new FormData();
    formData.append("file", file);
    formData.append("user_id", user_id);
    if (session_id) {
        formData.append("session_id", session_id);
    }

    try {
        const response = await fetch(`${baseUrl}/api/v1/InitialReview/analyze`, {
            method: "POST",
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