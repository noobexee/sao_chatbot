"use client";

import React, { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAudit } from './audit-context';

export default function AuditPage() {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false); // เพิ่ม state เพื่อบอกสถานะการอัปโหลด
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const { setCurrentFile } = useAudit();

  const handleFiles = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;

    const file = fileList[0];
    
    // 1. Update Context (เพื่อแสดงผล Preview ทันทีถ้าต้องการ)
    let simpleType: 'image' | 'pdf' | 'other' = 'other';
    if (file.type.startsWith('image/')) simpleType = 'image';
    else if (file.type === 'application/pdf') simpleType = 'pdf';

    setCurrentFile({
      id: "temp-pending", // ใส่ค่าชั่วคราวไปก่อน
      fileObj: file,
      name: file.name,
      type: simpleType,
      previewUrl: URL.createObjectURL(file),
    });

    // 2. เตรียมข้อมูลส่งไป Backend
    const formData = new FormData();
    formData.append("file", file);

    setIsUploading(true); // เริ่ม Loading

    try {
      // 3. ยิง API ไปที่ Backend
      const response = await fetch("http://localhost:8000/upload_document", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (data.status === "success" && data.audit_id) {
        console.log("Upload Success, ID:", data.audit_id);
        
        // 4. เปลี่ยนหน้าโดยแนบ ID ไปด้วย (Query Param หรือ Dynamic Route)
        // กรณีคุณใช้หน้า /audit/new-project และอยากส่ง ID ไปด้วย:
        router.push(`/audit/new-project?id=${data.audit_id}`);
        
        // หรือถ้าคุณมี Dynamic Route เช่น /audit/[id] ให้ใช้:
        // router.push(`/audit/${data.audit_id}`);
      } else {
        alert("Upload failed: " + data.message);
      }
    } catch (error) {
      console.error("Error uploading file:", error);
      alert("Something went wrong uploading the file.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(false); };
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div className="flex h-full flex-col bg-white">
      {/* Loading Overlay (Optional) */}
      {isUploading && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="text-white text-xl font-bold">Uploading & Saving...</div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-8 flex items-center justify-center">
        <div className="w-full max-w-4xl space-y-8">
          
          {/* Dropzone */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => !isUploading && fileInputRef.current?.click()} // ป้องกันกดซ้ำตอนโหลด
            className={`
              flex flex-col items-center justify-center p-12 text-center border-4 border-dashed rounded-xl cursor-pointer transition-all
              ${isDragging 
                ? 'border-red-400 bg-red-50 text-red-600 scale-[1.02]' 
                : 'border-gray-300 bg-gray-50 text-gray-500 hover:border-red-300 hover:text-red-500'
              }
            `}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => handleFiles(e.target.files)}
              className="hidden"
              accept=".pdf,.doc,.docx,.xlsx,.txt,image/*"
            />
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-white shadow-md border border-gray-200 text-3xl font-light text-[#a83b3b]">
              {isUploading ? "..." : "+"}
            </div>
            <p className="font-semibold text-lg">
               {isUploading ? "Uploading..." : "Drag and drop files here"}
            </p>
            <p className="text-sm text-gray-400 mt-2">PDF, Images, DOCX, XLSX</p>
          </div>

        </div>
      </div>
    </div>
  );
}