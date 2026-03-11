import { getBaseUrl } from "../config";

export interface SessionItem {
    session_id: string;
    last_updated: string;
    criteria_count: number;
}

function getAuthHeaders() {
    const token = localStorage.getItem("token");

    return {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
    };
}

export async function getUserSessions(): Promise<SessionItem[]> {
    const res = await fetch(`${getBaseUrl()}/api/v1/InitialReview/sessions`, {
        headers: getAuthHeaders(),
    });

    if (!res.ok) {
        throw new Error("Failed to fetch sessions");
    }

    return res.json();
}

export async function deleteSession(sessionId: string): Promise<boolean> {
    const res = await fetch(
        `${getBaseUrl()}/api/v1/InitialReview/sessions/${sessionId}`,
        {
            method: "DELETE",
            headers: getAuthHeaders(),
        }
    );

    return res.ok;
}
