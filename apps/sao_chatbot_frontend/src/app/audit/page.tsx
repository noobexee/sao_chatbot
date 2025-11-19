"use client";

import React, { useState, useRef, useEffect } from 'react';

// Enhanced interface to store the actual File object and preview URL
interface AuditFile {
  id: number;
  fileObj: File;      // The raw file object (needed for preview)
  name: string;
  size: string;
  type: 'image' | 'pdf' | 'other'; // Simplified type for rendering logic
  previewUrl: string; // The blob URL for the browser to display
}

export default function AuditPage() {
  const [files, setFiles] = useState<AuditFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  // Track which file is currently open to show the preview
  const [expandedFileId, setExpandedFileId] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // CLEANUP: When component unmounts or files change, revoke URLs to free memory
  useEffect(() => {
    return () => {
      files.forEach(file => {
        if (file.previewUrl) URL.revokeObjectURL(file.previewUrl);
      });
    };
  }, [files]);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList) return;

    const newFiles: AuditFile[] = Array.from(fileList).map((file, index) => {
      // Determine simple type for preview logic
      let simpleType: 'image' | 'pdf' | 'other' = 'other';
      if (file.type.startsWith('image/')) simpleType = 'image';
      else if (file.type === 'application/pdf') simpleType = 'pdf';

      return {
        id: Date.now() + index,
        fileObj: file,
        name: file.name,
        size: formatFileSize(file.size),
        type: simpleType,
        previewUrl: URL.createObjectURL(file), // Generate the preview URL here
      };
    });

    setFiles((prevFiles) => [...prevFiles, ...newFiles]);
  };

  // Toggle preview visibility
  const togglePreview = (id: number) => {
    setExpandedFileId(prev => (prev === id ? null : id));
  };

  // --- Drag & Drop Handlers ---
  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(false); };
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files);
    if (fileInputRef.current) fileInputRef.current.value = ''; 
  };

  return (
    <div className="flex h-full flex-col bg-white">
      <div className="flex-1 overflow-y-auto p-8">
        <div className="mx-auto max-w-4xl space-y-8">
          
          {/* --- Dropzone --- */}
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
              onChange={handleInputChange}
              className="hidden"
              multiple
              accept=".pdf,.doc,.docx,.xlsx,.txt,image/*"
            />
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-white shadow-md border border-gray-200 text-3xl font-light text-[#a83b3b]">
              +
            </div>
            <p className="font-semibold text-lg">Drag and drop files here</p>
            <p className="text-sm text-gray-400 mt-2">PDF, Images, DOCX, XLSX</p>
          </div>

          {/* --- File List with Previews --- */}
          {files.length > 0 && (
            <div className="pt-4">
              <h2 className="text-lg font-bold mb-4 text-[#1e293b] flex items-center gap-2">
                Uploaded Files 
                <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded-full text-xs">{files.length}</span>
              </h2>
              
              <ul className="space-y-4">
                {files.map((file) => (
                  <li key={file.id} className="group border border-gray-200 rounded-xl shadow-sm overflow-hidden bg-white transition-shadow hover:shadow-md">
                    
                    {/* Header Row (Click to Expand) */}
                    <div 
                        className="flex items-center justify-between p-4 cursor-pointer bg-white hover:bg-gray-50 select-none"
                        onClick={() => togglePreview(file.id)}
                    >
                        <div className="flex items-center gap-4">
                            {/* Icon based on type */}
                            <div className={`
                                p-2 rounded-lg 
                                ${file.type === 'pdf' ? 'bg-red-100 text-red-600' : 
                                  file.type === 'image' ? 'bg-blue-100 text-blue-600' : 
                                  'bg-gray-100 text-gray-600'}
                            `}>
                                {file.type === 'image' ? (
                                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                                ) : file.type === 'pdf' ? (
                                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/></svg>
                                ) : (
                                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
                                )}
                            </div>
                            <div>
                                <p className="font-medium text-gray-800">{file.name}</p>
                                <p className="text-xs text-gray-500">{file.size}</p>
                            </div>
                        </div>

                        <div className="flex items-center gap-4">
                             {/* Delete Button */}
                            <button 
                                onClick={(e) => {
                                    e.stopPropagation(); // Prevent expansion when deleting
                                    setFiles(files.filter(f => f.id !== file.id));
                                }}
                                className="text-gray-400 hover:text-red-500 p-2 rounded-full hover:bg-red-50 transition-colors"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                            </button>
                            
                            {/* Chevron Icon (Rotates when open) */}
                            <svg 
                                xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                                className={`text-gray-400 transition-transform duration-200 ${expandedFileId === file.id ? 'rotate-180' : ''}`}
                            >
                                <polyline points="6 9 12 15 18 9"></polyline>
                            </svg>
                        </div>
                    </div>

                    {/* --- PREVIEW PANEL --- */}
                    {expandedFileId === file.id && (
                        <div className="border-t border-gray-100 bg-gray-50 p-4">
                            
                            {file.type === 'image' ? (
                                <div className="relative w-full h-80 rounded-lg overflow-hidden border border-gray-200 bg-white flex items-center justify-center">
                                    {/* Image Preview */}
                                    <img 
                                        src={file.previewUrl} 
                                        alt="Preview" 
                                        className="max-w-full max-h-full object-contain" 
                                    />
                                </div>
                            ) : file.type === 'pdf' ? (
                                <div className="w-full h-96 border border-gray-200 rounded-lg bg-white">
                                    {/* PDF Preview */}
                                    <iframe 
                                        src={file.previewUrl} 
                                        className="w-full h-full rounded-lg" 
                                        title="PDF Preview" 
                                    />
                                </div>
                            ) : (
                                <div className="flex flex-col items-center justify-center h-32 text-gray-500 border border-dashed border-gray-300 rounded-lg">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mb-2 opacity-50"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                                    <p className="text-sm">Preview not available for this file type.</p>
                                </div>
                            )}
                            
                        </div>
                    )}

                  </li>
                ))}
              </ul>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}