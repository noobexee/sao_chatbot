import { getBaseUrl } from "../config";

export async function getAuditFile(auditId: string): Promise<Blob> {
    const baseUrl = getBaseUrl();
    try {
        const response = await fetch(`${baseUrl}/api/v1/audit/${auditId}/file`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch file: ${response.statusText}`);
        }
        
        return await response.blob();
    } catch (error) {
        console.error("API Error (getAuditFile):", error);
        throw error;
    }
}