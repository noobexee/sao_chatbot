"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useInitialReview } from './InitialReview-context';

export default function InitialReviewMainPage() {
    const router = useRouter();
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);
    
    const { setCurrentFile } = useInitialReview();
    const fileInputRef = useRef<HTMLInputElement>(null);

    //  จำลอง User ID
    const userId = "test_user_001"; 

    useEffect(() => {
        fetchHistory();
    }, []);

    const fetchHistory = async () => {
        try {
            // ปรับ port และ endpoint ให้ตรงกับ Backend
            const res = await fetch(`http://localhost:8000/api/v1/InitialReview/sessions/${userId}`);
            if (res.ok) {
                const data = await res.json();
                setSessions(data);
            }
        } catch (error) {
            console.error("Failed to fetch sessions", error);
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteSession = async (sessionId: string) => {
        if (!window.confirm("คุณแน่ใจหรือไม่ว่าต้องการลบประวัติการตรวจสอบนี้?")) return;
        
        try {
            const res = await fetch(`http://localhost:8000/api/v1/InitialReview/sessions/${userId}/${sessionId}`, {
                method: 'DELETE'
            });
            
            if (res.ok) {
                fetchHistory();
            } else {
                alert("ลบข้อมูลไม่สำเร็จ");
            }
        } catch (error) {
            console.error("Failed to delete session", error);
            alert("เกิดข้อผิดพลาดในการเชื่อมต่อ");
        }
    };

    const handleFileSelect = (fileList: FileList | null) => {
        if (!fileList || fileList.length === 0) return;
        const selectedFile = fileList[0];
        
        setCurrentFile({
            id: selectedFile.name,
            fileObj: selectedFile,
            previewUrl: URL.createObjectURL(selectedFile),
            type: selectedFile.type.startsWith('image/') ? 'image' : selectedFile.type === 'application/pdf' ? 'pdf' : 'other',
            name: selectedFile.name
        });

        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }

        router.push('/InitialReview/process');
    };

    return (
        <div className="p-8 max-w-6xl mx-auto min-h-screen">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-gray-800">ประวัติการตรวจสอบเอกสารเบื้องต้น</h1>
                    <p className="text-gray-500 text-sm mt-1">History for {userId}</p>
                </div>
                
                <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    onChange={(e) => handleFileSelect(e.target.files)}
                    accept=".pdf,.jpg,.jpeg,.png"
                />

                <button 
                    onClick={() => fileInputRef.current?.click()}
                    className="bg-blue-600 text-white px-5 py-2.5 rounded-lg hover:bg-blue-700 font-medium shadow-sm transition-colors"
                >
                    + สร้างการตรวจสอบใหม่
                </button>
            </div>
            
            {loading ? (
                <div className="flex justify-center py-20 text-gray-500 animate-pulse">
                    กำลังโหลดข้อมูลประวัติ...
                </div>
            ) : (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <table className="w-full text-left">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="p-4 font-semibold text-gray-600 text-sm">Session ID</th>
                                <th className="p-4 font-semibold text-gray-600 text-sm">จำนวนข้อที่บันทึก</th>
                                <th className="p-4 font-semibold text-gray-600 text-sm">อัปเดตล่าสุด</th>
                                <th className="p-4 font-semibold text-gray-600 text-sm text-center">จัดการ</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {sessions.length === 0 ? (
                                <tr>
                                    <td colSpan={4} className="p-8 text-center text-gray-500">
                                        ยังไม่มีประวัติการตรวจสอบเอกสาร <br/>
                                        กดปุ่ม "+ สร้างการตรวจสอบใหม่" ด้านบนเพื่อเริ่มอัปโหลดไฟล์
                                    </td>
                                </tr>
                            ) : (
                                sessions.map((session: any) => (
                                    <tr key={session.session_id} className="hover:bg-gray-50 transition-colors">
                                        <td className="p-4 text-sm font-mono text-gray-700">
                                            {session.session_id.substring(0, 8)}...
                                        </td>
                                        <td className="p-4 text-sm text-gray-700">
                                            <span className="inline-flex items-center justify-center bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full font-bold text-xs mr-2">
                                                {session.criteria_count}
                                            </span>
                                            รายการ
                                        </td>
                                        <td className="p-4 text-sm text-gray-600">
                                            {new Date(session.last_updated).toLocaleString('th-TH')}
                                        </td>
                                        <td className="p-4 flex items-center justify-center gap-4">
                                            <button 
                                                onClick={() => router.push(`/InitialReview/${session.session_id}`)}
                                                className="text-blue-600 hover:text-blue-800 text-sm font-semibold transition-colors"
                                            >
                                                เปิดดู
                                            </button>
                                            <button 
                                                onClick={() => handleDeleteSession(session.session_id)}
                                                className="text-red-500 hover:text-red-700 text-sm font-semibold transition-colors"
                                            >
                                                ลบ
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}