import { getBaseUrl } from "../config";

export interface ReviewSummaryData {
    session_id: string;
    OCR_text: string | null;

    criteria_1: boolean | null;
    criteria_2: boolean | null;
    criteria_3: boolean | null;

    // [official, entity, time_place, behavior]
    criteria_4: [boolean | null, boolean | null, boolean | null, boolean | null] | null;

    criteria_5: boolean | null;

    // [name (null=fake name), citizen_id, address]
    criteria_6: [boolean | null, boolean | null, boolean | null] | null;

    // key = found (false=ปรากฏ/true=ไม่ปรากฏ)
    criteria_7: { [key: string]: string | null } | null;

    // key = case type (false=บางประเด็น/true=ไม่อยู่ใน ผตง.)
    criteria_8: { [key: string]: string | null } | null;
}

export async function getReviewSummary(sessionId: string): Promise<ReviewSummaryData> {
    const baseUrl = getBaseUrl();
    const token = localStorage.getItem("token");

    const response = await fetch(
        `${baseUrl}/api/v1/InitialReview/${sessionId}/summary`,
        {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        }
    );

    if (!response.ok) {
        throw new Error(`Failed to fetch summary: ${response.statusText}`);
    }

    const result: ReviewSummaryData = await response.json();
    return result;
}