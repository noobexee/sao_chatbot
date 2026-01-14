"use client";

import React, { useState } from "react";
import Image from "next/image";
import { useAudit } from "../audit-context";

// --- Types ---
type StepStatus = "neutral" | "pending" | "success" | "fail";
type FeedbackType = "up" | "down" | null;

interface Person {
  name: string;
  role: string;
}

// Editable Step 4 Details
interface Step4Details {
  entity: string | null;
  behavior: string | null;
  official: string | null;
  date: string | null;
  location: string | null;
}

interface AuditStep {
  id: number;
  label: string;
  type: "auto" | "manual"; 
  status: StepStatus;
  options?: { label: string; value: "success" | "fail" }[];
  selectedOption?: string | null;
  isProcessing?: boolean;
  
  // Feedback field
  feedback?: FeedbackType;

  ocrResult?: {
    status: "success" | "fail";
    title: string;
    reason?: string;
    people?: Person[];
    details?: Step4Details;
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
    status: "pending", 
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
    status: "pending",
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
  const [expandedStepIds, setExpandedStepIds] = useState<number[]>([]);

  // Editing States
  const [editingField, setEditingField] = useState<keyof Step4Details | null>(null);
  const [tempEditValue, setTempEditValue] = useState("");

  const toggleExpand = (id: number) => {
    setExpandedStepIds(prev => 
      prev.includes(id) 
        ? prev.filter(stepId => stepId !== id)
        : [...prev, id]
    );
  };

  const handleToggleAll = () => {
    const allIds = steps.map(s => s.id);
    const isAllOpen = expandedStepIds.length === allIds.length;
    if (isAllOpen) setExpandedStepIds([]);
    else setExpandedStepIds(allIds);
  };

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

  // --- HANDLE FEEDBACK (UPDATED) ---
  const handleFeedback = (stepId: number, type: FeedbackType) => {
    // Just update state, no console.log
    setSteps(prev => prev.map(step => {
        if (step.id === stepId) {
            const newFeedback = step.feedback === type ? null : type;
            return { ...step, feedback: newFeedback };
        }
        return step;
    }));
  };

  const handleStartAnalysis = async () => {
    if (!currentFile) {
        alert("No file loaded!");
        return;
    }

    setShowChecklist(true);
    setSteps(prev => prev.map(step => 
      (step.id === 4 || step.id === 6) ? { ...step, isProcessing: true } : step
    ));

    try {
        const formData = new FormData();
        formData.append("file", currentFile.fileObj);

        const response = await fetch("http://localhost:8080/analyze", {
            method: "POST",
            body: formData,
        });

        const result = await response.json();

        if (result.status === "success") {
            const { step4, step6 } = result.data;

            setSteps(prev => prev.map(step => {
                if (step.id === 4) {
                    return {
                        ...step,
                        isProcessing: false,
                        status: step4.status,
                        ocrResult: step4
                    };
                }
                if (step.id === 6) {
                    return {
                        ...step,
                        isProcessing: false,
                        status: step6.status,
                        ocrResult: {
                            status: step6.status,
                            title: step6.title,
                            reason: step6.reason, 
                            people: step6.people
                        }
                    };
                }
                return step;
            }));

            setExpandedStepIds(prev => [...new Set([...prev, 4, 6])]);
        } else {
            // Minimal error handling, removed specific console errors for cleaner demo code if needed
            // keeping basic error alert for functionality
            setSteps(prev => prev.map(s => ({...s, isProcessing: false})));
            alert("Backend Error"); 
        }

    } catch (error) {
        setSteps(prev => prev.map(s => ({...s, isProcessing: false})));
        alert("Backend Connection Failed");
    }
  };

  // --- EDITING LOGIC ---
  const startEditing = (key: keyof Step4Details, currentValue: string | null) => {
    setEditingField(key);
    setTempEditValue(currentValue || "");
  };

  const saveEdit = (key: keyof Step4Details) => {
    setSteps(prev => prev.map(step => {
        if (step.id === 4 && step.ocrResult && step.ocrResult.details) {
            return {
                ...step,
                ocrResult: {
                    ...step.ocrResult,
                    details: {
                        ...step.ocrResult.details,
                        [key]: tempEditValue
                    }
                }
            };
        }
        return step;
    }));
    setEditingField(null);
  };

  const cancelEdit = () => {
    setEditingField(null);
    setTempEditValue("");
  };

  const getStatusClasses = (status: StepStatus) => {
    switch (status) {
      case "pending": return "bg-yellow-50 border-yellow-200 text-yellow-900";
      case "success": return "bg-green-50 border-green-200 text-green-900";
      case "fail":    return "bg-red-50 border-red-200 text-red-900";
      default:        return "bg-white border-gray-200 text-gray-800";
    }
  };

  // Helper to render Step 4 items
  const renderStep4Item = (fieldKey: keyof Step4Details, label: string, value: string | null, required: boolean) => {
    const isEditing = editingField === fieldKey;

    return (
        <div className="flex items-start justify-between text-sm py-2 border-b border-gray-100 last:border-0 group/item">
            <div className="flex flex-col flex-1 mr-2">
                <span className="text-gray-600 font-medium mb-1">
                    {label} {required && <span className="text-red-500">*</span>}
                </span>
                
                {isEditing ? (
                    <div className="flex gap-2 mt-1">
                        <input 
                            type="text" 
                            className="border border-blue-300 rounded px-2 py-1 text-sm w-full focus:outline-none focus:ring-2 focus:ring-blue-100"
                            value={tempEditValue}
                            onChange={(e) => setTempEditValue(e.target.value)}
                            autoFocus
                        />
                        <button onClick={() => saveEdit(fieldKey)} className="text-green-600 hover:text-green-800 font-bold px-1">✓</button>
                        <button onClick={cancelEdit} className="text-red-500 hover:text-red-700 font-bold px-1">✕</button>
                    </div>
                ) : (
                    <div className="flex items-center gap-2 group-hover/item:bg-gray-50 rounded px-1 -ml-1 transition-colors">
                        {value ? (
                            <span className="text-gray-800 font-bold">{value}</span>
                        ) : (
                            <span className="text-gray-400 italic">ไม่พบข้อมูล</span>
                        )}
                        <button 
                            onClick={() => startEditing(fieldKey, value)}
                            className="opacity-0 group-hover/item:opacity-100 text-blue-400 hover:text-blue-600 transition-opacity p-1"
                            title="Edit"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path></svg>
                        </button>
                    </div>
                )}
            </div>
            {!isEditing && (
                <div className="ml-2 flex items-center h-full pt-1">
                    {value ? (
                        <span className="text-green-600 font-bold">✓</span>
                    ) : (
                        required ? <span className="text-red-500 font-bold">✕</span> : <span className="text-gray-300">-</span>
                    )}
                </div>
            )}
        </div>
    );
  };

  return (
    <div className="flex h-full w-full flex-row overflow-hidden bg-[#f9fafb]">
      
      {/* LEFT PANEL */}
      <div className="flex-1 overflow-y-auto p-8 flex justify-center bg-[#f0f2f5]">
        <div className="h-full w-full max-w-[800px] min-h-[1000px] bg-white shadow-sm border border-gray-200 relative">
          {currentFile ? (
             currentFile.type === 'pdf' ? (
              <iframe src={currentFile.previewUrl} className="w-full h-full" title="Doc" />
             ) : currentFile.type === 'image' ? (
              <img src={currentFile.previewUrl} alt="Doc" className="w-full h-full object-contain" />
             ) : (
              <div className="flex flex-col justify-center items-center h-full text-gray-500 gap-2">
                  <div className="text-4xl">📄</div>
                  <div>{currentFile.name}</div>
                  <div className="text-sm">Preview not supported</div>
              </div>
             )
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 p-10">
              <h2 className="text-xl font-bold">No Document</h2>
            </div>
          )}
        </div>
      </div>

      {/* RIGHT PANEL */}
      <div className="w-[500px] shrink-0 flex flex-col gap-6 border-l border-gray-200 bg-white p-6 overflow-y-auto">
        
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
            <div className="flex h-full flex-col bg-white">
                <div className="space-y-3 pb-4">
                    {steps.map((step) => (
                    <div key={step.id}>
                        {/* Step Header */}
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
                                    Processing...
                                </span>
                             )}
                             
                             {!expandedStepIds.includes(step.id) && !step.isProcessing && step.status !== 'neutral' && (
                                <div className={`mt-1 text-xs font-bold ${step.status === 'success' ? 'text-green-700' : 'text-red-700'}`}>
                                    {step.type === 'manual' && step.selectedOption && (
                                        <span>Selected: {step.selectedOption}</span>
                                    )}
                                    {/* Show Pass/Fail for 4 */}
                                    {step.id === 4 && (step.status === 'success' ? 'Result: Pass' : 'Result: Fail')}
                                </div>
                             )}
                          </div>
                          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform duration-200 ${expandedStepIds.includes(step.id) ? 'rotate-180' : ''} opacity-50`}>
                            <polyline points="6 9 12 15 18 9"></polyline>
                          </svg>
                        </div>

                        {/* EXPANDED CONTENT */}
                        {expandedStepIds.includes(step.id) && (
                           <div className="mt-2 ml-4 p-4 border-l-2 border-gray-200 bg-gray-50 rounded-r-md">
                              
                              {/* MANUAL STEPS (3, 5) */}
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

                              {/* STEP 4: EDITABLE LIST */}
                              {step.id === 4 && step.ocrResult && step.ocrResult.details && (
                                <div className="space-y-2 bg-white p-2 rounded border border-gray-100">
                                    <div className="flex justify-between items-center mb-2">
                                        <p className="text-xs font-bold text-gray-500 uppercase">ตรวจสอบองค์ประกอบ (Required*)</p>
                                    </div>
                                    {renderStep4Item("official", "เจ้าหน้าที่ผู้ถูกร้อง", step.ocrResult.details.official, true)}
                                    {renderStep4Item("entity", "ชื่อหน่วยรับตรวจ", step.ocrResult.details.entity, true)}
                                    {renderStep4Item("behavior", "พฤติการณ์", step.ocrResult.details.behavior, true)}
                                    <p className="text-xs font-bold text-gray-500 uppercase mt-4 mb-2">ข้อมูลเพิ่มเติม (Optional)</p>
                                    {renderStep4Item("date", "วันเวลา", step.ocrResult.details.date, false)}
                                    {renderStep4Item("location", "สถานที่", step.ocrResult.details.location, false)}
                                </div>
                              )}

                              {/* STEP 6: People List */}
                              {step.id === 6 && step.ocrResult && (
                                <div className="space-y-3">
                                    {step.ocrResult.people && step.ocrResult.people.length > 0 ? (
                                        <div className="bg-white border border-gray-200 rounded-md overflow-hidden">
                                            <div className="bg-gray-100 px-3 py-2 text-xs font-bold text-gray-500 uppercase flex justify-between">
                                                <span>Detected People</span>
                                                <span className="bg-gray-200 text-gray-600 px-1.5 rounded-full">{step.ocrResult.people.length}</span>
                                            </div>
                                            <div className="divide-y divide-gray-100 max-h-60 overflow-y-auto">
                                                {step.ocrResult.people.map((person, idx) => (
                                                    <div key={idx} className="px-3 py-2 text-sm flex items-center justify-between hover:bg-gray-50">
                                                        <span className="font-medium text-gray-800 truncate max-w-[180px]">{person.name}</span>
                                                        <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${
                                                            person.role === 'ผู้ร้องเรียน' ? 'bg-blue-100 text-blue-700' :
                                                            person.role === 'ผู้ถูกร้องเรียน' ? 'bg-red-100 text-red-700' :
                                                            'bg-gray-100 text-gray-600'
                                                        }`}>
                                                            {person.role}
                                                        </span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="text-sm text-gray-500 italic p-2 text-center">
                                            ไม่พบรายชื่อบุคคลในเอกสาร
                                        </div>
                                    )}
                                </div>
                              )}

                              {/* FEEDBACK SECTION (Under Data) */}
                              {(step.id === 4 || step.id === 6) && step.ocrResult && (
                                <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-end gap-2">
                                    <span className="text-xs text-gray-400">Is this result correct?</span>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); handleFeedback(step.id, "up"); }}
                                        className={`p-1.5 rounded transition-colors ${
                                            step.feedback === "up" ? "bg-green-50 text-green-600 ring-1 ring-green-200" : "text-gray-400 hover:text-green-600 hover:bg-gray-50"
                                        }`}
                                        title="Correct"
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2h0a3.13 3.13 0 0 1 3 3.88Z"/></svg>
                                    </button>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); handleFeedback(step.id, "down"); }}
                                        className={`p-1.5 rounded transition-colors ${
                                            step.feedback === "down" ? "bg-red-50 text-red-600 ring-1 ring-red-200" : "text-gray-400 hover:text-red-600 hover:bg-gray-50"
                                        }`}
                                        title="Incorrect"
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 14V2"/><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22h0a3.13 3.13 0 0 1-3-3.88Z"/></svg>
                                    </button>
                                </div>
                              )}

                           </div>
                        )}
                    </div>
                    ))}
                </div>

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

        {/* CHAT INTERFACE */}
         <div className="flex-1 overflow-hidden mt-auto pt-6">
             <div className="flex flex-col rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden min-h-[300px]">
                <div className="flex flex-col items-center justify-center pt-6 pb-4">
                    <div className="mb-2 relative h-16 w-16">
                        <Image src="/logo.png" alt="SAO Logo" fill className="object-contain" />
                    </div>
                    <h3 className="text-sm font-bold text-[#1e293b]">SAO chatbot as assistance</h3>
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

      </div>
    </div>
  );
}