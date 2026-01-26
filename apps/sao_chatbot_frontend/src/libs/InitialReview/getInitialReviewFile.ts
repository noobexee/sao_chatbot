import { getBaseUrl } from "../config";

export async function getInitialReviewFile(InitialReviewId: string): Promise<Blob> {
    const baseUrl = getBaseUrl();
    try {
        const response = await fetch(`${baseUrl}/api/v1/InitialReview/${InitialReviewId}/file`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch file: ${response.statusText}`);
        }
        
        return await response.blob();
    } catch (error) {
        console.error("API Error (getInitialReviewFile):", error);
        throw error;
    }
}