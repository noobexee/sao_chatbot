"use client";

import React, { useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useInitialReview } from './InitialReview-context';

export default function InitialReviewUploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { setCurrentFile } = useInitialReview();

  const handleFileSelect = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    const selectedFile = fileList[0];
    
    // 1. Save to Context (Memory Only)
    setCurrentFile({
      id: "temp-id",
      fileObj: selectedFile,
      previewUrl: URL.createObjectURL(selectedFile),
      type: selectedFile.type.startsWith('image/') ? 'image' : selectedFile.type === 'application/pdf' ? 'pdf' : 'other',
      name: selectedFile.name
    });

    // 2. Navigate to Process Page immediately
    // ไม่ต้องรอ upload เพราะเราจะส่งไฟล์ไปวิเคราะห์ที่หน้าถัดไปเลย
    router.push('/InitialReview/process');
  };

  return (
    <div className="flex h-full flex-col bg-white items-center justify-center p-8">
      <div className="w-full max-w-4xl text-center space-y-8">
        <h1 className="text-3xl font-bold text-gray-800">Initial Review Process</h1>
        <p className="text-gray-500">อัปโหลดเอกสารเพื่อเริ่มการตรวจสอบเบื้องต้น (Single Session)</p>
        
        <div
          onClick={() => fileInputRef.current?.click()}
          className="border-4 border-dashed border-gray-300 bg-gray-50 rounded-xl p-16 cursor-pointer hover:border-red-300 hover:bg-red-50 transition-all"
        >
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files)}
            accept=".pdf,.jpg,.png"
          />
          <div className="text-6xl mb-4">📂</div>
          <p className="text-xl font-semibold text-gray-700">คลิกเพื่ออัปโหลดไฟล์</p>
        </div>
      </div>
    </div>
  );
}