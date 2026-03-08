"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getReviewSummary, ReviewSummaryData } from "../../../libs/InitialReview/getSummaray";

export default function ReviewSummaryPage() {

    const params = useParams();
    const sessionId = params.session_id as string;

    const [summary, setSummary] = useState<ReviewSummaryData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {

        if (!sessionId) return;

        async function load() {
            try {
                const data = await getReviewSummary(sessionId);
                setSummary(data);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        }

        load();

    }, [sessionId]);

    if (loading) return <div className="p-6">Loading...</div>;
    if (!summary) return <div className="p-6">No data</div>;

    return (
        <div className="p-6 space-y-6">

            <h2 className="text-2xl font-bold">Review Summary</h2>

            {/* Session */}
            <div>
                <b>Session:</b> {summary.session_id}
            </div>

            {/* OCR */}
            <div>
                <b>OCR Text</b>
                <pre className="bg-gray-100 p-3 rounded whitespace-pre-wrap">
                    {summary.OCR_text ?? "None"}
                </pre>
            </div>

            {/* Criteria 1 */}
            <div>
                <b>Criteria 1:</b> {summary.criteria_1 === null ? "Not evaluated" : summary.criteria_1 ? "True" : "False"}
            </div>

            {/* Criteria 2 */}
            <div>
                <b>Criteria 2:</b> {summary.criteria_2 === null ? "Not evaluated" : summary.criteria_2 ? "True" : "False"}
            </div>

            {/* Criteria 3 */}
            <div>
                <b>Criteria 3:</b> {summary.criteria_3 === null ? "Not evaluated" : summary.criteria_3 ? "True" : "False"}
            </div>

            {/* Criteria 4 */}
            {summary.criteria_4 && (
                <div>
                    <b>Criteria 4</b>
                    <ul className="list-disc ml-6">
                        <li>Official: {summary.criteria_4[0] ? "Found" : "Not Found"}</li>
                        <li>Entity: {summary.criteria_4[1] ? "Found" : "Not Found"}</li>
                        <li>Time / Place: {summary.criteria_4[2] ? "Found" : "Not Found"}</li>
                        <li>Behavior: {summary.criteria_4[3] ? "Found" : "Not Found"}</li>
                    </ul>
                </div>
            )}

            {/* Criteria 5 */}
            <div>
                <b>Criteria 5:</b> {summary.criteria_5 === null ? "Not evaluated" : summary.criteria_5 ? "True" : "False"}
            </div>

            {/* Criteria 6 */}
            {summary.criteria_6 && (
                <div>
                    <b>Criteria 6</b>
                    <ul className="list-disc ml-6">
                        <li>
                            Name: {
                                summary.criteria_6[0] === null
                                    ? "Anonymous / Fake Name"
                                    : summary.criteria_6[0]
                                        ? "Provided"
                                        : "Not Provided"
                            }
                        </li>
                        <li>
                            Citizen ID: {summary.criteria_6[1] ? "Provided" : "Not Provided"}
                        </li>
                        <li>
                            Address: {summary.criteria_6[2] ? "Provided" : "Not Provided"}
                        </li>
                    </ul>
                </div>
            )}

            {/* Criteria 7 */}
            {summary.criteria_7 && (
                <div>
                    <b>Criteria 7</b>

                    {"false" in summary.criteria_7 && (
                        <div>
                            พบหน่วยงานที่เกี่ยวข้อง: {summary.criteria_7["false"]}
                        </div>
                    )}

                    {"true" in summary.criteria_7 && (
                        <div>
                            ไม่พบหน่วยงานที่เกี่ยวข้อง
                        </div>
                    )}

                </div>
            )}

            {/* Criteria 8 */}
            {summary.criteria_8 && (
                <div>
                    <b>Criteria 8</b>

                    {"false" in summary.criteria_8 && (
                        <div>
                            อยู่ในอำนาจสำนักงานการตรวจเงินแผ่นดิน
                            <div className="text-gray-700 mt-2">
                                {summary.criteria_8["false"]}
                            </div>
                        </div>
                    )}

                    {"true" in summary.criteria_8 && (
                        <div>
                            ไม่อยู่ในอำนาจสำนักงานการตรวจเงินแผ่นดิน
                            <div className="text-gray-700 mt-2">
                                {summary.criteria_8["true"]}
                            </div>
                        </div>
                    )}

                </div>
            )}

        </div>
    );
}