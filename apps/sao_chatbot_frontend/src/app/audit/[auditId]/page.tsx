"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import { useSearchParams, useParams } from "next/navigation";
import { useAudit } from "../audit-context";

// Import API Functions

import { getAuditFile } from "../../../libs/audit/getAuditFile";
import { analyzeDocument } from "../../../libs/audit/analyzeDocument";
import { saveAiResult } from "../../../libs/audit/saveAIResult";

// --- Types ---
type StepStatus = "neutral" | "pending" | "success" | "fail";
type FeedbackType = "up" | "down" | null;

interface Person { name: string; role: string; }

interface FieldData {
  value: string | null;      
  original: string | null;   
  isEdited: boolean;         
}

const createField = (val: string | null): FieldData => ({
  value: val,
  original: val,
  isEdited: false
});

interface Step4Details {
  entity: FieldData;
  behavior: FieldData;
  official: FieldData;
  date: FieldData;
  location: FieldData;
}

interface AuditStep {
  id: number;
  label: string;
  type: "auto" | "manual"; 
  status: StepStatus;
  options?: { label: string; value: "success" | "fail" }[];
  selectedOption?: string | null;
  isProcessing?: boolean;
  feedback?: FeedbackType;
  ocrResult?: {
    status: "success" | "fail";
    title: string;
    reason?: string;
    people?: Person[];
    details?: Step4Details; 
  };
}

const initialSteps: AuditStep[] = [
  { id: 1, label: "1. เป็นหน่วยรับตรวจที่อยู่ในสำนักตรวจสอบ", type: "auto", status: "neutral" },
  { id: 2, label: "2. เป็นเรื่องที่อยู่ในหน้าที่ของผู้ว่าการตรวจเงินแผ่นดิน", type: "auto", status: "neutral" },
  { id: 3, label: "3. เป็นเรื่องที่เกิดขึ้นมาไม่เกิน 5 ปี...", type: "manual", status: "pending", options: [{ label: "เกิน", value: "fail" }, { label: "ไม่เกิน", value: "success" }, { label: "ไม่ระบุ", value: "fail" }], selectedOption: null },
  { id: 4, label: "4. เป็นเรื่องที่ระบุรายละเอียดเพียงพอที่จะตรวจสอบได้", type: "auto", status: "neutral", isProcessing: false },
  { id: 5, label: "5. เป็นเรื่องที่ผู้ว่าการ...", type: "manual", status: "pending", options: [{ label: "เคย", value: "fail" }, { label: "ไม่เคย", value: "success" }], selectedOption: null },
  { id: 6, label: "6. รายละเอียดของผู้ร้องเรียน", type: "auto", status: "neutral", isProcessing: false },
  { id: 7, label: "7. ไม่เป็นเรื่องร้องเรียนที่อยู่ระหว่างการดำเนินการของหน่วยงานอื่น", type: "auto", status: "neutral" },
  { id: 8, label: "8. เป็นเรื่องร้องเรียนที่อยู่ในอำนาจหน้าที่ขององค์กรอิสระอื่น", type: "auto", status: "neutral" },
];

export default function AuditProjectPage() {
  const params = useParams(); 
  const searchParams = useSearchParams();
  const { currentFile, setCurrentFile } = useAudit();

  const pathAuditId = params?.auditId as string;
  const auditId = (pathAuditId && pathAuditId !== 'new-project') 
    ? pathAuditId 
    : searchParams.get('id');

  const [isLoadingFile, setIsLoadingFile] = useState(false);
  const [showChecklist, setShowChecklist] = useState(false);
  const [steps, setSteps] = useState<AuditStep[]>(initialSteps);
  const [expandedStepIds, setExpandedStepIds] = useState<number[]>([]);
  const [isSaving, setIsSaving] = useState(false); 
  const [editingField, setEditingField] = useState<keyof Step4Details | null>(null);
  const [tempEditValue, setTempEditValue] = useState("");

  // --- 1. Fetch File Logic ---
  useEffect(() => {
    const fetchFileFromDB = async () => {
        if (currentFile || !auditId) return;

        setIsLoadingFile(true);
        try {
            console.log(`🔄 Recovering file for ID: ${auditId}`);

            // API Call 1: Get Info
            //const infoJson = await getAuditInfo(auditId);
            //if (infoJson.status !== 'success') throw new Error("Info fetch failed");
            //const fileName = infoJson.data.file_name;

            // API Call 2: Get File Blob
            const blob = await getAuditFile(auditId);
            
            let type: 'image' | 'pdf' | 'other' = 'other';
            if (blob.type === 'application/pdf') type = 'pdf';
            else if (blob.type.startsWith('image/')) type = 'image';

            //const fileObj = new File([blob], fileName, { type: blob.type });
            //const previewUrl = URL.createObjectURL(blob);

            //console.log("✅ File recovered:", fileName);

            //setCurrentFile({
            //    id: auditId,
            //    fileObj: fileObj,
            //    name: fileName,
            //    type: type,
            //    previewUrl: previewUrl
            //});

        } catch (error) {
            console.error("❌ Error fetching file:", error);
        } finally {
            setIsLoadingFile(false);
        }
    };

    fetchFileFromDB();
  }, [auditId, currentFile, setCurrentFile]);

  // --- 2. Start Analysis Logic ---
  const handleStartAnalysis = async () => {
    if (!currentFile) { alert("No file loaded!"); return; }

    setShowChecklist(true);
    setSteps(prev => prev.map(step => (step.id === 4 || step.id === 6) ? { ...step, isProcessing: true } : step));

    try {
        // API Call 3: Analyze Document
        const result = await analyzeDocument(currentFile.fileObj);

        if (result.status === "success") {
            const { step4, step6 } = result.data;

            setSteps(prev => prev.map(step => {
                if (step.id === 4) {
                    const structuredDetails: Step4Details = {
                        entity: createField(step4.details?.entity || null),
                        behavior: createField(step4.details?.behavior || null),
                        official: createField(step4.details?.official || null),
                        date: createField(step4.details?.date || null),
                        location: createField(step4.details?.location || null)
                    };
                    return { ...step, isProcessing: false, status: step4.status, ocrResult: { ...step4, details: structuredDetails } };
                }
                if (step.id === 6) {
                    return { ...step, isProcessing: false, status: step6.status, ocrResult: { status: step6.status, title: step6.title, reason: step6.reason, people: step6.people } };
                }
                return step;
            }));
            setExpandedStepIds(prev => [...new Set([...prev, 4, 6])]);
        } else {
            setSteps(prev => prev.map(s => ({...s, isProcessing: false})));
            alert("Backend Error: " + (result.message || "Unknown error")); 
        }
    } catch (error) {
        console.error(error);
        setSteps(prev => prev.map(s => ({...s, isProcessing: false})));
        alert("Backend Connection Failed");
    }
  };

  // --- 3. Save Logic ---
  const handleSaveToDatabase = async () => {
    if (!auditId) {
      alert("Error: Audit ID missing.");
      return;
    }

    setIsSaving(true);
    try {
      console.log(`💾 Saving data for Audit ID: ${auditId}`);
      
      const stepsToSave = steps.filter(s => s.ocrResult || s.status !== 'neutral');
      
      for (const step of stepsToSave) {
          let resultData = step.ocrResult || {};
          if(step.type === 'manual') {
             resultData = { ...resultData, manual_selection: step.selectedOption, status: step.status };
          }

          // API Call 4: Save AI Result
          await saveAiResult({
              audit_id: auditId,
              step_id: step.id,
              result: resultData
          });
      }

      alert(`✅ Saved successfully! (ID: ${auditId})`);

    } catch (error) {
      console.error("Save Error:", error);
      alert("Error saving data: " + error);
    } finally {
      setIsSaving(false);
    }
  };

  // --- UI Helpers ---
  const toggleExpand = (id: number) => {
    setExpandedStepIds(prev => prev.includes(id) ? prev.filter(stepId => stepId !== id) : [...prev, id]);
  };

  const handleToggleAll = () => {
    const allIds = steps.map(s => s.id);
    setExpandedStepIds(expandedStepIds.length === allIds.length ? [] : allIds);
  };

  const handleOptionSelect = (stepId: number, optionLabel: string, resultStatus: "success" | "fail") => {
    setSteps(prevSteps => prevSteps.map(step => step.id === stepId ? { ...step, status: resultStatus, selectedOption: optionLabel } : step));
  };

  const handleFeedback = (stepId: number, type: FeedbackType) => {
    setSteps(prev => prev.map(step => step.id === stepId ? { ...step, feedback: step.feedback === type ? null : type } : step));
  };

  const getStatusClasses = (status: StepStatus) => {
    switch (status) {
      case "pending": return "bg-yellow-50 border-yellow-200 text-yellow-900";
      case "success": return "bg-green-50 border-green-200 text-green-900";
      case "fail":    return "bg-red-50 border-red-200 text-red-900";
      default:        return "bg-white border-gray-200 text-gray-800";
    }
  };

  const startEditing = (key: keyof Step4Details, field: FieldData) => { setEditingField(key); setTempEditValue(field.value || ""); };
  const cancelEdit = () => { setEditingField(null); setTempEditValue(""); };
  const saveEdit = (key: keyof Step4Details) => { 
    setSteps(prev => prev.map(step => { 
        if (step.id === 4 && step.ocrResult && step.ocrResult.details) { 
            return { 
                ...step, 
                ocrResult: { 
                    ...step.ocrResult, 
                    details: { 
                        ...step.ocrResult.details, 
                        [key]: { ...step.ocrResult.details[key], value: tempEditValue, isEdited: true } 
                    } 
                } 
            }; 
        } 
        return step; 
    })); 
    setEditingField(null); 
  };

  const renderStep4Item = (fieldKey: keyof Step4Details, label: string, field: FieldData | undefined, required: boolean) => {
    if (!field) return null;
    const isEditing = editingField === fieldKey;
    const displayValue = field.value;

    return (
        <div className="flex items-start justify-between text-sm py-2 border-b border-gray-100 last:border-0 group/item">
            <div className="flex flex-col flex-1 mr-2">
                <span className="text-gray-600 font-medium mb-1">
                    {label} {required && <span className="text-red-500">*</span>}
                    {field.isEdited && <span className="text-xs text-orange-500 ml-2">(Edited)</span>}
                </span>
                
                {isEditing ? (
                    <div className="flex gap-2 mt-1">
                        <input type="text" className="border border-blue-300 rounded px-2 py-1 text-sm w-full focus:outline-none focus:ring-2 focus:ring-blue-100" value={tempEditValue} onChange={(e) => setTempEditValue(e.target.value)} autoFocus />
                        <button onClick={() => saveEdit(fieldKey)} className="text-green-600 hover:text-green-800 font-bold px-1">✓</button>
                        <button onClick={cancelEdit} className="text-red-500 hover:text-red-700 font-bold px-1">✕</button>
                    </div>
                ) : (
                    <div className="flex items-center gap-2 group-hover/item:bg-gray-50 rounded px-1 -ml-1 transition-colors">
                        {displayValue ? (
                            <span className={`font-bold ${field.isEdited ? 'text-gray-900' : 'text-gray-800'}`}>{displayValue}</span>
                        ) : (
                            <span className="text-gray-400 italic">ไม่พบข้อมูล</span>
                        )}
                        <button onClick={() => startEditing(fieldKey, field)} className="opacity-0 group-hover/item:opacity-100 text-blue-400 hover:text-blue-600 transition-opacity p-1" title="Edit">✎</button>
                    </div>
                )}
            </div>
            {!isEditing && (
                <div className="ml-2 flex items-center h-full pt-1">
                    {displayValue ? <span className="text-green-600 font-bold">✓</span> : (required ? <span className="text-red-500 font-bold">✕</span> : <span className="text-gray-300">-</span>)}
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
          
          {isLoadingFile ? (
             <div className="flex flex-col items-center justify-center h-full text-gray-500 gap-3">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[#a83b3b]"></div>
                <p className="font-medium text-gray-600">Retrieving Document...</p>
             </div>
          ) : currentFile ? (
             currentFile.type === 'pdf' ? (
              <iframe src={currentFile.previewUrl} className="w-full h-full" title="Doc" />
             ) : currentFile.type === 'image' ? (
              <img src={currentFile.previewUrl} alt="Doc" className="w-full h-full object-contain" />
             ) : (
              <div className="flex flex-col justify-center items-center h-full text-gray-500 gap-2">
                  <div className="text-4xl">📄</div>
                  <div className="font-semibold">{currentFile.name}</div>
                  <div className="text-sm">Preview not supported for this file type</div>
              </div>
             )
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 p-10">
                <h2 className="text-xl font-bold">No Document Found</h2>
                <p className="text-sm mt-2">Please upload a document first</p>
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
                กรุณาตรวจสอบเอกสารว่าโหลดสมบูรณ์แล้ว จากนั้นกด "Start" เพื่อเริ่มวิเคราะห์
              </p>
              <button 
                onClick={handleStartAnalysis} 
                disabled={isLoadingFile || !currentFile} 
                className={`w-full px-6 py-2 rounded-lg border transition-all text-sm font-medium shadow-sm 
                    ${(isLoadingFile || !currentFile) 
                        ? 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed' 
                        : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50 hover:border-gray-400'
                    }`}
              >
                {isLoadingFile ? "Loading..." : "Start Analysis"}
              </button>
            </div>
        ) : (
            <div className="flex h-full flex-col bg-white">
                <div className="space-y-3 pb-4">
                    {steps.map((step) => (
                    <div key={step.id}>
                        <div 
                            className={`flex items-center justify-between rounded-md border p-4 shadow-sm cursor-pointer transition-all duration-300 ${getStatusClasses(step.status)}`} 
                            onClick={() => toggleExpand(step.id)}
                        >
                          <div className="flex-1 pr-4">
                             <div className="flex items-center gap-2"><span className="text-sm font-medium">{step.label}</span></div>
                             {step.isProcessing && <span className="inline-flex items-center gap-1 mt-1 text-xs text-blue-600 font-semibold animate-pulse">Processing...</span>}
                             {!expandedStepIds.includes(step.id) && !step.isProcessing && step.status !== 'neutral' && (
                                <div className={`mt-1 text-xs font-bold ${step.status === 'success' ? 'text-green-700' : 'text-red-700'}`}>
                                    {step.type === 'manual' && step.selectedOption && <span>Selected: {step.selectedOption}</span>}
                                    {step.id === 4 && (step.status === 'success' ? 'Result: Pass' : 'Result: Fail')}
                                </div>
                             )}
                          </div>
                          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform duration-200 ${expandedStepIds.includes(step.id) ? 'rotate-180' : ''} opacity-50`}><polyline points="6 9 12 15 18 9"></polyline></svg>
                        </div>

                        {expandedStepIds.includes(step.id) && (
                           <div className="mt-2 ml-4 p-4 border-l-2 border-gray-200 bg-gray-50 rounded-r-md">
                              {step.type === "manual" && step.options && (
                                 <div className="space-y-2">
                                    <p className="text-xs font-bold text-gray-500 mb-2 uppercase">Manual Verification</p>
                                    {step.options.map((option) => (
                                      <label key={option.label} className="flex items-center gap-3 cursor-pointer group p-2 rounded hover:bg-white hover:shadow-sm">
                                        <input type="radio" name={`step-${step.id}`} className="h-4 w-4 text-[#a83b3b] focus:ring-[#a83b3b]" checked={step.selectedOption === option.label} onChange={() => handleOptionSelect(step.id, option.label, option.value)} />
                                        <span className={`text-sm ${step.selectedOption === option.label ? 'font-bold text-gray-900' : 'text-gray-600'}`}>{option.label}</span>
                                      </label>
                                    ))}
                                 </div>
                              )}

                              {step.id === 4 && step.ocrResult && step.ocrResult.details && (
                                <div className="space-y-2 bg-white p-2 rounded border border-gray-100">
                                    <div className="flex justify-between items-center mb-2"><p className="text-xs font-bold text-gray-500 uppercase">ตรวจสอบองค์ประกอบ (Required*)</p></div>
                                    {renderStep4Item("official", "เจ้าหน้าที่ผู้ถูกร้อง", step.ocrResult.details.official, true)}
                                    {renderStep4Item("entity", "ชื่อหน่วยรับตรวจ", step.ocrResult.details.entity, true)}
                                    {renderStep4Item("behavior", "พฤติการณ์", step.ocrResult.details.behavior, true)}
                                    <p className="text-xs font-bold text-gray-500 uppercase mt-4 mb-2">ข้อมูลเพิ่มเติม (Optional)</p>
                                    {renderStep4Item("date", "วันเวลา", step.ocrResult.details.date, false)}
                                    {renderStep4Item("location", "สถานที่", step.ocrResult.details.location, false)}
                                </div>
                              )}

                              {step.id === 6 && step.ocrResult && (
                                <div className="space-y-3">
                                    {step.ocrResult.people && step.ocrResult.people.length > 0 ? (
                                        <div className="bg-white border border-gray-200 rounded-md overflow-hidden">
                                            <div className="bg-gray-100 px-3 py-2 text-xs font-bold text-gray-500 uppercase flex justify-between"><span>Detected People</span><span className="bg-gray-200 text-gray-600 px-1.5 rounded-full">{step.ocrResult.people.length}</span></div>
                                            <div className="divide-y divide-gray-100 max-h-60 overflow-y-auto">
                                                {step.ocrResult.people.map((person, idx) => (
                                                    <div key={idx} className="px-3 py-2 text-sm flex items-center justify-between hover:bg-gray-50">
                                                        <span className="font-medium text-gray-800 truncate max-w-[180px]">{person.name}</span>
                                                        <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${person.role === 'ผู้ร้องเรียน' ? 'bg-blue-100 text-blue-700' : person.role === 'ผู้ถูกร้องเรียน' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'}`}>{person.role}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ) : ( <div className="text-sm text-gray-500 italic p-2 text-center">ไม่พบรายชื่อบุคคลในเอกสาร</div> )}
                                </div>
                              )}

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

                <div className="pt-4 mt-auto border-t border-gray-100 flex flex-col gap-3">
                    <button onClick={handleToggleAll} className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 w-full font-medium transition-colors">{expandedStepIds.length === steps.length ? 'ย่อทั้งหมด' : 'ขยายทั้งหมด'}</button>
                    <button 
                        onClick={handleSaveToDatabase} 
                        disabled={isSaving || !currentFile} 
                        className={`w-full px-6 py-2 rounded-lg border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 transition-all text-sm font-medium shadow-sm flex items-center justify-center gap-2 ${(isSaving || !currentFile) ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                        {isSaving ? "Saving..." : "Summarize & Save"}
                    </button>
                </div>
            </div>
        )}

         <div className="flex-1 overflow-hidden mt-auto pt-6">
             <div className="flex flex-col rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden min-h-[300px]">
                <div className="flex flex-col items-center justify-center pt-6 pb-4">
                    <div className="mb-2 relative h-16 w-16"><Image src="/logo.png" alt="SAO Logo" fill className="object-contain" /></div>
                    <h3 className="text-sm font-bold text-[#1e293b]">SAO chatbot as assistance</h3>
                </div>
                <div className="flex-1 bg-white p-4"></div>
                <div className="p-4 pt-0 pb-6">
                    <div className="relative flex items-center rounded-full border border-gray-200 bg-white px-2 py-2 shadow-sm focus-within:ring-1 focus-within:ring-gray-200">
                        <input type="text" placeholder="ส่งข้อความให้ SAO bot" className="flex-1 border-none bg-transparent px-4 text-sm outline-none placeholder:text-gray-400" />
                        <button className="flex h-8 w-8 items-center justify-center rounded-full bg-[#a83b3b] text-white hover:bg-[#8f3232] transition-colors shrink-0">➤</button>
                    </div>
                </div>
            </div>
        </div>

      </div>
    </div>
  );
}