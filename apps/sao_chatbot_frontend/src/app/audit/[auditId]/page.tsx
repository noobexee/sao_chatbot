"use client";

import React, { useState } from "react";
import Image from "next/image";
import { useAudit } from "../audit-context";

// --- Types ---
type StepStatus = "neutral" | "pending" | "success" | "fail";

interface AuditStep {
  id: number;
  label: string;
  type: "auto" | "manual"; 
  status: StepStatus;
  options?: { label: string; value: "success" | "fail" }[];
  selectedOption?: string | null;
  isProcessing?: boolean;
  ocrResult?: {
    status: "success" | "fail";
    title: string;
    reason: string;
  };
}

// --- Initial Data ---
const initialSteps: AuditStep[] = [
  { id: 1, label: "1. เป็นหน่วยรับตรวจที่อยู่ในสำนักตรวจสอบ", type: "auto", status: "neutral" },
  { id: 2, label: "2. เป็นเรื่องที่อยู่ในหน้าที่ของผู้ว่าการตรวจเงินแผ่นดิน", type: "auto", status: "neutral" },
  {
    id: 3,
    label: "3. เป็นเรื่องที่เกิดขึ้นมาไม่เกิน 5 ปี นับตั้งแต่วันที่เกิดเหตุจนถึงวันที่สตง.ได้รับเรื่อง",
    type: "manual",
    status: "pending", // Yellow
    options: [
      { label: "เกิน", value: "fail" },
      { label: "ไม่เกิน", value: "success" },
      { label: "ไม่ระบุ", value: "fail" },
    ],
    selectedOption: null,
  },
  { 
    id: 4, 
    label: "4. เป็นเรื่องที่ระบุรายละเอียดเพียงพอที่จะตรวจสอบได้", 
    type: "auto", 
    status: "neutral", 
    isProcessing: false,
  },
  {
    id: 5,
    label: "5. เป็นเรื่องที่ผู้ว่าการหรือผู้ที่ผู้ว่าการมอบหมายให้ตรวจสอบแล้วยังไม่เคยแจ้งผลการตรวจสอบ",
    type: "manual",
    status: "pending", // Yellow
    options: [
      { label: "เคย", value: "fail" },
      { label: "ไม่เคย", value: "success" },
    ],
    selectedOption: null,
  },
  { 
    id: 6, 
    label: "6. รายละเอียดของผู้ร้องเรียน", 
    type: "auto", 
    status: "neutral",
    isProcessing: false,
  },
  { id: 7, label: "7. ไม่เป็นเรื่องร้องเรียนที่อยู่ระหว่างการดำเนินการของหน่วยงานอื่น", type: "auto", status: "neutral" },
  { id: 8, label: "8. เป็นเรื่องร้องเรียนที่อยู่ในอำนาจหน้าที่ขององค์กรอิสระอื่น", type: "auto", status: "neutral" },
];

export default function AuditProjectPage({ params }: { params: { auditId: string } }) {
  const { currentFile } = useAudit();
  const [showChecklist, setShowChecklist] = useState(false);
  const [steps, setSteps] = useState<AuditStep[]>(initialSteps);
  
  // CHANGED: Now using an array to support multiple open steps
  const [expandedStepIds, setExpandedStepIds] = useState<number[]>([]);

  // Toggle single step
  const toggleExpand = (id: number) => {
    setExpandedStepIds(prev => 
      prev.includes(id) 
        ? prev.filter(stepId => stepId !== id) // Close if open
        : [...prev, id] // Open if closed
    );
  };

  // Toggle All Steps
  const handleToggleAll = () => {
    // Check if all are currently open
    const allIds = steps.map(s => s.id);
    const isAllOpen = expandedStepIds.length === allIds.length;

    if (isAllOpen) {
      setExpandedStepIds([]); // Collapse all
    } else {
      setExpandedStepIds(allIds); // Expand all
    }
  };

  // --- Logic for Manual Selection ---
  const handleOptionSelect = (stepId: number, optionLabel: string, resultStatus: "success" | "fail") => {
    setSteps(prevSteps => 
      prevSteps.map(step => {
        if (step.id === stepId) {
          return { ...step, status: resultStatus, selectedOption: optionLabel };
        }
        return step;
      })
    );
  };

  // --- Logic for "One Go" Analysis ---
  const handleStartAnalysis = () => {
    setShowChecklist(true);
    
    // Set auto steps to processing
    setSteps(prev => prev.map(step => 
      (step.id === 4 || step.id === 6) ? { ...step, isProcessing: true } : step
    ));

    // Simulate API Call
    setTimeout(() => {
        finishAnalysis();
    }, 2500);
  };

  const finishAnalysis = () => {
    // Mock Result for Step 4
    const step4Success = Math.random() > 0.3;
    const step4Result = {
        status: step4Success ? "success" : "fail",
        title: step4Success 
            ? "เป็นเรื่องที่ระบุรายละเอียดเพียงพอที่จะตรวจสอบได้"
            : "เป็นเรื่องที่ระบุรายละเอียดไม่เพียงพอที่จะตรวจสอบได้",
        reason: step4Success 
            ? "เนื่องจากมีการระบุชื่อผู้ถูกร้องเรียน (นายฉลาด หลักแหลม) ตำแหน่ง และพฤติการณ์การกระทำผิด (การนำรถหลวงไปใช้ส่วนตัว) รวมถึงระบุวันเวลาที่เกิดเหตุ (1-3 กันยายน 2566) ไว้อย่างชัดเจนตามระเบียบข้อ 18(3)"
            : "เนื่องจากขาดข้อมูลระบุวันเวลาที่ชัดเจนของการกระทำความผิด และไม่ได้ระบุสถานที่เกิดเหตุ ทำให้ไม่สามารถดำเนินการตรวจสอบข้อเท็จจริงต่อได้"
    } as const;

    // Mock Result for Step 6
    const step6Result = {
        status: "success",
        title: "รายละเอียดของผู้ร้องเรียนครบถ้วน",
        reason: "มีการระบุชื่อ นามสกุล และที่อยู่ของผู้ร้องเรียน (นายรู้รักษ์ เงินแผ่นดิน) ชัดเจน"
    } as const;

    setSteps(prev => prev.map(step => {
        if (step.id === 4) {
            return {
                ...step,
                isProcessing: false,
                status: step4Result.status,
                ocrResult: step4Result
            };
        }
        if (step.id === 6) {
            return {
                ...step,
                isProcessing: false,
                status: step6Result.status as "success" | "fail",
                ocrResult: step6Result
            };
        }
        return step;
    }));

    // Auto-expand relevant steps to show results
    setExpandedStepIds(prev => [...new Set([...prev, 4, 6])]);
  };

  const getStatusClasses = (status: StepStatus) => {
    switch (status) {
      case "pending": return "bg-yellow-50 border-yellow-200 text-yellow-900";
      case "success": return "bg-green-50 border-green-200 text-green-900";
      case "fail":    return "bg-red-50 border-red-200 text-red-900";
      default:        return "bg-white border-gray-200 text-gray-800";
    }
  };

  return (
    <div className="flex h-full w-full flex-row overflow-hidden bg-[#f9fafb]">
      
      {/* LEFT: Document Viewer */}
      <div className="flex-1 overflow-y-auto p-8 flex justify-center bg-[#f0f2f5]">
        <div className="h-full w-full max-w-[800px] min-h-[1000px] bg-white shadow-sm border border-gray-200 relative">
          {currentFile ? (
             currentFile.type === 'pdf' ? (
              <iframe src={currentFile.previewUrl} className="w-full h-full" title="Doc" />
             ) : currentFile.type === 'image' ? (
              <img src={currentFile.previewUrl} alt="Doc" className="w-full h-full object-contain" />
             ) : (
              <div className="flex items-center justify-center h-full text-gray-500">{currentFile.name}</div>
             )
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 p-10">
              <h2 className="text-xl font-bold">No Document</h2>
            </div>
          )}
        </div>
      </div>

      {/* RIGHT: Tools */}
      <div className="w-[500px] shrink-0 flex flex-col gap-6 border-l border-gray-200 bg-white p-6 overflow-y-auto">
        
        {/* START SCREEN */}
        {!showChecklist ? (
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold text-[#1e293b] mb-2">เริ่มต้นการตรวจสอบด้วย AI</h2>
              <p className="text-sm text-gray-500 mb-6 leading-relaxed">
                กรุณาโปรดตรวจสอบเอกสารและกรอกข้อมูลเอกสารให้ครบถ้วนก่อนกด "Start" เพื่อประสิทธิภาพสูงสุด
              </p>
              <button 
                onClick={handleStartAnalysis}
                className="px-6 py-2 rounded-lg border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 hover:border-gray-400 transition-all text-sm font-medium shadow-sm"
              >
                Start
              </button>
            </div>
        ) : (
            /* CHECKLIST SCREEN */
            <div className="flex h-full flex-col bg-white">
                <div className="space-y-3 pb-4">
                    {steps.map((step) => (
                    <div key={step.id}>
                        {/* Step Card */}
                        <div 
                          className={`
                            flex items-center justify-between rounded-md border p-4 shadow-sm cursor-pointer transition-all duration-300
                            ${getStatusClasses(step.status)}
                          `}
                          onClick={() => toggleExpand(step.id)}
                        >
                          <div className="flex-1 pr-4">
                             <div className="flex items-center gap-2">
                                <span className="text-sm font-medium">{step.label}</span>
                             </div>

                             {step.isProcessing && (
                                <span className="inline-flex items-center gap-1 mt-1 text-xs text-blue-600 font-semibold animate-pulse">
                                    <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                                    Processing OCR...
                                </span>
                             )}
                             {step.selectedOption && !expandedStepIds.includes(step.id) && (
                               <div className="mt-1 text-xs font-bold opacity-80">Selected: {step.selectedOption}</div>
                             )}
                             {step.ocrResult && !expandedStepIds.includes(step.id) && !step.isProcessing && (
                                <div className={`mt-1 text-xs font-bold ${step.status === 'success' ? 'text-green-700' : 'text-red-700'}`}>
                                    Result: {step.status === 'success' ? 'Pass' : 'Fail'}
                                </div>
                             )}
                          </div>
                          
                          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform duration-200 ${expandedStepIds.includes(step.id) ? 'rotate-180' : ''} opacity-50`}>
                            <polyline points="6 9 12 15 18 9"></polyline>
                          </svg>
                        </div>

                        {/* EXPANDED AREA */}
                        {expandedStepIds.includes(step.id) && (
                           <div className="mt-2 ml-4 p-4 border-l-2 border-gray-200 bg-gray-50 rounded-r-md">
                              
                              {/* A. Manual Input */}
                              {step.type === "manual" && step.options && (
                                 <div className="space-y-2">
                                    <p className="text-xs font-bold text-gray-500 mb-2 uppercase">Manual Verification</p>
                                    {step.options.map((option) => (
                                      <label key={option.label} className="flex items-center gap-3 cursor-pointer group p-2 rounded hover:bg-white hover:shadow-sm">
                                        <input 
                                            type="radio" 
                                            name={`step-${step.id}`}
                                            className="h-4 w-4 text-[#a83b3b] focus:ring-[#a83b3b]"
                                            checked={step.selectedOption === option.label}
                                            onChange={() => handleOptionSelect(step.id, option.label, option.value)}
                                        />
                                        <span className={`text-sm ${step.selectedOption === option.label ? 'font-bold text-gray-900' : 'text-gray-600'}`}>{option.label}</span>
                                      </label>
                                    ))}
                                 </div>
                              )}

                              {/* B. AI Result */}
                              {step.type === "auto" && (
                                <>
                                    {step.isProcessing ? (
                                        <div className="flex items-center gap-3 text-sm text-gray-500 py-4">
                                            <svg className="animate-spin h-5 w-5 text-blue-500" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                                            Analyzing document content...
                                        </div>
                                    ) : step.ocrResult ? (
                                        <div className={`p-4 rounded-lg border ${step.status === 'success' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                                            <p className={`font-bold text-sm mb-2 ${step.status === 'success' ? 'text-green-800' : 'text-red-800'}`}>
                                                {step.ocrResult.title}
                                            </p>
                                            <p className="text-sm text-gray-700 leading-relaxed">
                                                <span className="font-semibold">เพราะ: </span>
                                                {step.ocrResult.reason}
                                            </p>
                                        </div>
                                    ) : (
                                        <p className="text-sm text-gray-400 italic">Waiting to start analysis...</p>
                                    )}
                                </>
                              )}

                           </div>
                        )}
                    </div>
                    ))}
                </div>

                {/* EXPAND ALL BUTTON */}
                <div className="pt-4 mt-auto border-t border-gray-100">
                    <button 
                        onClick={handleToggleAll}
                        className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 w-full font-medium transition-colors"
                    >
                        {expandedStepIds.length === steps.length ? 'ย่อทั้งหมด (Collapse All)' : 'ขยายทั้งหมด (Expand All)'}
                    </button>
                </div>
            </div>
        )}

        {/* MINI CHAT (Always Visible) */}
        {!showChecklist && (
             <div className="flex-1 overflow-hidden mt-auto">
                 <div className="flex flex-col rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden min-h-[400px]">
                    <div className="flex flex-col items-center justify-center pt-10 pb-6">
                        <div className="mb-4 relative h-24 w-24">
                            <Image src="/logo.png" alt="SAO Logo" fill className="object-contain" />
                        </div>
                        <h3 className="text-base font-bold text-[#1e293b]">SAO chatbot as assistance</h3>
                    </div>
                    <div className="flex-1 bg-white p-4"></div>
                    <div className="p-4 pt-0 pb-6">
                        <div className="relative flex items-center rounded-full border border-gray-200 bg-white px-2 py-2 shadow-sm focus-within:ring-1 focus-within:ring-gray-200">
                            <input type="text" placeholder="ส่งข้อความให้ SAO bot" className="flex-1 border-none bg-transparent px-4 text-sm outline-none placeholder:text-gray-400" />
                            <button className="flex h-8 w-8 items-center justify-center rounded-full bg-[#a83b3b] text-white hover:bg-[#8f3232] transition-colors shrink-0">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        )}
      </div>
    </div>
  );
}