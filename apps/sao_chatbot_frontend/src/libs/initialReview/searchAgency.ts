import { getBaseUrl } from "../config";

export async function searchAgencyManual(query: string): Promise<any> {
    const baseUrl = getBaseUrl();
    try {
        const response = await fetch(`${baseUrl}/api/v1/InitialReview/search_agency?q=${encodeURIComponent(query)}`, {
            method: "GET",
        });

        if (!response.ok) {
            throw new Error(`Failed to search agency: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error("API Error (searchAgencyManual):", error);
        throw error;
    }
}
