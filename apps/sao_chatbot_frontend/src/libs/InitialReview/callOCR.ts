import { getBaseUrl } from "../config";

// Interface specifically for the OCR-only response
export interface OcrResponse {
    status: string;
    text: string;      // The full extracted text
    page_count?: number; // Optional: if your backend returns page count
}

/**
 * Uploads a file to perform OCR only (no AI analysis).
 * Returns the raw extracted text.
 */
export async function ocrDocument(file: File): Promise<OcrResponse> {
    const baseUrl = getBaseUrl();
    const formData = new FormData();
    formData.append("file", file);

    try {
        // Assuming your new backend endpoint is mapped to /ocr
        const response = await fetch(`${baseUrl}/api/v1/InitialReview/ocr`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const errorBody = await response.text(); 
            throw new Error(`OCR failed: ${response.statusText} - ${errorBody}`);
        }

        return await response.json();
    } catch (error) {
        console.error("API Error (ocrDocument):", error);
        throw error;
    }
}