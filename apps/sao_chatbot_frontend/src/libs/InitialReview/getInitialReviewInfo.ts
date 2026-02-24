import { getBaseUrl } from "../config";

export interface InitialReviewInfoResponse {
    status: string;
    data: {
        InitialReview_id: string;
        file_name: string;
        created_at: string;
    };
    message?: string;
}

export async function getInitialReviewInfo(InitialReviewId: string): Promise<InitialReviewInfoResponse> {
    const baseUrl = getBaseUrl();
    try {
        const response = await fetch(`${baseUrl}/api/v1/InitialReview/${InitialReviewId}/info`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch info: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error("API Error (getInitialReviewInfo):", error);
        throw error;
    }
}