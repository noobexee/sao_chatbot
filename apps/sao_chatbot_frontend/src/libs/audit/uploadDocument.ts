import { getBaseUrl } from "../config";

export interface UploadResponse {
    status: string;
    audit_id: string;
    message?: string;
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
    const baseUrl = getBaseUrl();
    
    const formData = new FormData();
    formData.append("file", file);

    try {
        // ✅ แก้ URL ให้ตรงกับ Controller ใหม่ (/api/v1 + /audit + /upload)
        const response = await fetch(`${baseUrl}/api/v1/audit/upload`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            let errorMsg = "Failed to upload document";
            try {
                const errorText = await response.text();
                // พยายาม parse JSON, ถ้าไม่ได้ก็ใช้ text ดิบ
                try {
                    const errorData = JSON.parse(errorText);
                    errorMsg = errorData.message || errorData.detail || errorMsg;
                } catch {
                    if (errorText) errorMsg = errorText;
                }
            } catch (e) {
                console.error("Error parsing error response", e);
            }
            throw new Error(errorMsg);
        }

        return await response.json();

    } catch (error) {
        console.error("API Call Failed:", error);
        throw error;
    }
}