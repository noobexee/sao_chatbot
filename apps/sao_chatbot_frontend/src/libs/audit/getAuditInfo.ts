import { getBaseUrl } from "../config";

export interface AuditInfoResponse {
    status: string;
    data: {
        audit_id: string;
        file_name: string;
        created_at: string;
    };
    message?: string;
}

export async function getAuditInfo(auditId: string): Promise<AuditInfoResponse> {
    const baseUrl = getBaseUrl();
    try {
        const response = await fetch(`${baseUrl}/api/v1/audit/${auditId}/info`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch info: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error("API Error (getAuditInfo):", error);
        throw error;
    }
}