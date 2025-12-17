"use client";

import React, { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAudit } from './audit-context';

export default function AuditPage() {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const { setCurrentFile } = useAudit(); // Get function from context

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;

    // We only take the first file for this demo flow
    const file = fileList[0];
    
    let simpleType: 'image' | 'pdf' | 'other' = 'other';
    if (file.type.startsWith('image/')) simpleType = 'image';
    else if (file.type === 'application/pdf') simpleType = 'pdf';

    // Save to Context
    setCurrentFile({
      id: Date.now().toString(),
      fileObj: file,
      name: file.name,
      type: simpleType,
      previewUrl: URL.createObjectURL(file),
    });

    // Navigate to the Detail Page
    // We use a dummy ID 'new' or generate one
    router.push(`/audit/new-project`); 
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
      <div className="flex-1 overflow-y-auto p-8 flex items-center justify-center">
        <div className="w-full max-w-4xl space-y-8">
          
          {/* Dropzone */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
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
              +
            </div>
            <p className="font-semibold text-lg">Drag and drop files here</p>
            <p className="text-sm text-gray-400 mt-2">PDF, Images, DOCX, XLSX</p>
          </div>

        </div>
      </div>
    </div>
  );
}