import { getBaseUrl } from "../config";

// You might want to define stricter types for the AI result here
export interface AnalyzeResponse {
    status: string;
    data: {
        criteria4: any; // Define detailed interface if needed
        criteria6: any;
        raw_text?: string;
    };
    message?: string;
}

export async function analyzeDocument(file: File): Promise<AnalyzeResponse> {
    const baseUrl = getBaseUrl();
    const formData = new FormData();
    formData.append("file", file);

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