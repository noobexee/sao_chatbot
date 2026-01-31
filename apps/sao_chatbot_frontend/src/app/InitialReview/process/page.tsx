"use client";

import React, { useState, useEffect } from "react";
import { useSearchParams, useParams } from "next/navigation";
import { useInitialReview } from "../InitialReview-context";

// --- Import API Functions from Libs ---
import { analyzeDocument } from "../../../libs/InitialReview/analyzeDocument";
import { saveAiResult } from "../../../libs/InitialReview/saveAIResult";
import { ocrDocument } from "../../../libs/InitialReview/callOCR"; 

// --- Types ---
type criteriaStatus = "neutral" | "pending" | "success" | "fail";
type FeedbackType = "up" | "down" | null;
type ViewMode = "pdf" | "text";

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

// สำหรับ Criteria 4 (Sufficiency)
interface criteria4Details {
  entity: FieldData;
  behavior: FieldData;
  official: FieldData;
  date: FieldData;
  location: FieldData;
}

// ✅ Interface ใหม่สำหรับ Criteria 2 & 8 (Authority Check)
interface AuthorityDetails {
  result: string;    // "เป็น" หรือ "ไม่เป็น"
  reason: string;    // คำอธิบาย
  evidence?: string; // ข้อความจาก OCR (ถ้ามี)
  organization?: string; // สำหรับ Criteria 8 (ชื่อองค์กร)
}

interface InitialReviewCriteria {
  id: number;
  label: string;
  type: "auto" | "manual"; 
  status: criteriaStatus;
  options?: { label: string; value: "success" | "fail" }[];
  selectedOption?: string | null;
  isProcessing?: boolean;
  feedback?: FeedbackType;
  ocrResult?: {
    status: "success" | "fail";
    title: string;
    reason?: string;
    people?: Person[];
    details?: criteria4Details; 
    authority?: AuthorityDetails; // ✅ เพิ่ม Field นี้สำหรับ Criteria 2 & 8
  };
}

const initialCriterias: InitialReviewCriteria[] = [
  { id: 1, label: "1. เป็นหน่วยรับตรวจที่อยู่ในสำนักตรวจสอบ", type: "auto", status: "neutral" },
  { id: 2, label: "2. เป็นเรื่องที่อยู่ในหน้าที่ของผู้ว่าการตรวจเงินแผ่นดิน", type: "auto", status: "neutral" },
  { id: 3, label: "3. เป็นเรื่องที่เกิดขึ้นมาไม่เกิน 5 ปี...", type: "manual", status: "pending", options: [{ label: "เกิน", value: "fail" }, { label: "ไม่เกิน", value: "success" }, { label: "ไม่ระบุ", value: "fail" }], selectedOption: null },
  { id: 4, label: "4. เป็นเรื่องที่ระบุรายละเอียดเพียงพอที่จะตรวจสอบได้", type: "auto", status: "neutral", isProcessing: false },
  { id: 5, label: "5. เป็นเรื่องที่ผู้ว่าการ...", type: "manual", status: "pending", options: [{ label: "เคย", value: "fail" }, { label: "ไม่เคย", value: "success" }], selectedOption: null },
  { id: 6, label: "6. รายละเอียดของผู้ร้องเรียน", type: "auto", status: "neutral", isProcessing: false },
  { id: 7, label: "7. ไม่เป็นเรื่องร้องเรียนที่อยู่ระหว่างการดำเนินการของหน่วยงานอื่น", type: "auto", status: "neutral" },
  { id: 8, label: "8. เป็นเรื่องร้องเรียนที่อยู่ในอำนาจหน้าที่ขององค์กรอิสระอื่น", type: "auto", status: "neutral" },
];

export default function InitialReviewProjectPage() {
  const params = useParams(); 
  const searchParams = useSearchParams();
  const { currentFile } = useInitialReview();

  const pathInitialReviewId = params?.InitialReviewId as string;
  const InitialReviewId = (pathInitialReviewId && pathInitialReviewId !== 'new-project') 
    ? pathInitialReviewId 
    : searchParams.get('id');

  // --- State ---
  const [isLoadingFile, setIsLoadingFile] = useState(false);
  const [showChecklist, setShowChecklist] = useState(false);
  const [criterias, setCriterias] = useState<InitialReviewCriteria[]>(initialCriterias);
  const [expandedCriteriaIds, setExpandedCriteriaIds] = useState<number[]>([]);
  const [isSaving, setIsSaving] = useState(false); 
  const [editingField, setEditingField] = useState<keyof criteria4Details | null>(null);
  const [tempEditValue, setTempEditValue] = useState("");

  // --- State: View & Edit Mode ---
  const [viewMode, setViewMode] = useState<ViewMode>("pdf");
  const [docText, setDocText] = useState<string>(""); 
  const [draftText, setDraftText] = useState(""); 
  const [isEditingText, setIsEditingText] = useState(false);

  // --- State: OCR Status ---
  const [isOCRLoading, setIsOCRLoading] = useState(false);
  const [ocrError, setOcrError] = useState<string | null>(null);
  const processedFileIdRef = React.useRef<string | null>(null);

  // --- 1. OCR Logic (Run Automatically) ---
  useEffect(() => {
    const runOCR = async () => {
        // Validation
        if (!currentFile?.fileObj) return;
        
        // STOP if we already processed this specific file ID
        // Assuming currentFile has a unique 'id' or we can use 'name' + 'size' as proxy
        const fileId = currentFile.id || currentFile.name; 
        if (processedFileIdRef.current === fileId) return;

        // STOP if text already exists (redundant check but good safety)
        if (docText) return; 

        // Mark as processing immediately
        processedFileIdRef.current = fileId;

        setIsOCRLoading(true);
        setOcrError(null);
        
        try {
            console.log(`🚀 Calling ocrDocument for: ${currentFile.name}`);
            const result = await ocrDocument(currentFile.fileObj);
            
            setDocText(result.text);
            setDraftText(result.text);
            setViewMode("text");
        } catch (err: any) {
            console.error("OCR Error:", err);
            setOcrError(err.message || "Failed to extract text");
            // Reset ref on error so user can retry? 
            // processedFileIdRef.current = null;
        } finally {
            setIsOCRLoading(false);
        }
    };

    runOCR();
  }, [currentFile]);

  // --- 2. Start Analysis Logic ---
  const handleStartAnalysis = async () => {
    if (!draftText.trim()) { 
        alert("No text to analyze. Please wait for OCR or type manually."); 
        return; 
    }

    setShowChecklist(true);
    // Set processing state for all auto criteria (2, 4, 6, 8)
    setCriterias(prev => prev.map(c => 
        ([2, 4, 6, 8].includes(c.id)) ? { ...c, isProcessing: true } : c
    ));

    try {
        const blob = new Blob([draftText], { type: "text/plain" });
        const fileToAnalyze = new File([blob], `${currentFile?.name || 'doc'}_edited.txt`, { type: "text/plain" });

        const result = await analyzeDocument(fileToAnalyze);

        if (result.status === "success" || result.data) {
            // Destructure all available results (including optional ones)
            const { criteria2, criteria4, criteria6, criteria8 } = result.data;

            setCriterias(prev => prev.map(c => {
                // ✅ Criteria 2: อำนาจหน้าที่ สตง.
                if (c.id === 2 && criteria2) {
                    return {
                        ...c,
                        isProcessing: false,
                        status: criteria2.status,
                        ocrResult: {
                            status: criteria2.status,
                            title: criteria2.title,
                            reason: criteria2.reason,
                            authority: {
                                result: criteria2.result, // "เป็น" หรือ "ไม่เป็น"
                                reason: criteria2.reason,
                                evidence: criteria2.evidence
                            }
                        }
                    };
                }

                // ✅ Criteria 4: Sufficiency
                if (c.id === 4 && criteria4) {
                    const structuredDetails: criteria4Details = {
                        entity: createField(criteria4.details?.entity?.value || criteria4.details?.entity || null),
                        behavior: createField(criteria4.details?.behavior?.value || criteria4.details?.behavior || null),
                        official: createField(criteria4.details?.official?.value || criteria4.details?.official || null),
                        date: createField(criteria4.details?.date?.value || criteria4.details?.date || null),
                        location: createField(criteria4.details?.location?.value || criteria4.details?.location || null)
                    };
                    return { ...c, isProcessing: false, status: criteria4.status, ocrResult: { ...criteria4, details: structuredDetails } };
                }

                // ✅ Criteria 6: Complainant
                if (c.id === 6 && criteria6) {
                    return { ...c, isProcessing: false, status: criteria6.status, ocrResult: { status: criteria6.status, title: criteria6.title, reason: criteria6.reason, people: criteria6.people } };
                }

                // ✅ Criteria 8: อำนาจองค์กรอิสระอื่น
                if (c.id === 8 && criteria8) {
                    return {
                        ...c,
                        isProcessing: false,
                        status: criteria8.status,
                        ocrResult: {
                            status: criteria8.status,
                            title: criteria8.title,
                            reason: criteria8.reason,
                            authority: {
                                result: criteria8.result,
                                reason: criteria8.reason,
                                evidence: criteria8.evidence,
                                organization: criteria8.organization
                            }
                        }
                    };
                }

                return c;
            }));
            
            // Expand relevant sections
            setExpandedCriteriaIds(prev => [...new Set([...prev, 2, 4, 6, 8])]);
        } else {
            throw new Error(result.message || "Unknown error");
        }
    } catch (error: any) {
        console.error(error);
        setCriterias(prev => prev.map(s => ({...s, isProcessing: false})));
        alert("Analysis Failed: " + error.message);
    }
  };

  // --- 3. Save Logic ---
  const handleSaveToDatabase = async () => {
    if (!InitialReviewId) {
      alert("Error: InitialReview ID missing.");
      return;
    }

    setIsSaving(true);
    try {
      const criteriasToSave = criterias.filter(s => s.ocrResult || s.status !== 'neutral');
      for (const criteria of criteriasToSave) {
          let resultData = criteria.ocrResult || {};
          if(criteria.type === 'manual') {
             resultData = { ...resultData, manual_selection: criteria.selectedOption, status: criteria.status };
          }
          await saveAiResult({
              InitialReview_id: InitialReviewId,
              criteria_id: criteria.id,
              result: resultData
          });
      }
      alert(`✅ Saved successfully!`);
    } catch (error: any) {
      console.error("Save Error:", error);
      alert("Error saving data: " + error.message);
    } finally {
      setIsSaving(false);
    }
  };

  // --- Helpers & UI ---
  const toggleExpand = (id: number) => {
    setExpandedCriteriaIds(prev => prev.includes(id) ? prev.filter(cId => cId !== id) : [...prev, id]);
  };

  const handleToggleAll = () => {
    const allIds = criterias.map(s => s.id);
    setExpandedCriteriaIds(expandedCriteriaIds.length === allIds.length ? [] : allIds);
  };

  const handleOptionSelect = (criteriaId: number, optionLabel: string, resultStatus: "success" | "fail") => {
    setCriterias(prevCriterias => prevCriterias.map(criteria => criteria.id === criteriaId ? { ...criteria, status: resultStatus as any, selectedOption: optionLabel } : criteria));
  };

  const handleFeedback = (criteriaId: number, type: FeedbackType) => {
    setCriterias(prev => prev.map(criteria => criteria.id === criteriaId ? { ...criteria, feedback: criteria.feedback === type ? null : type } : criteria));
  };

  const getStatusClasses = (status: criteriaStatus) => {
    switch (status) {
      case "pending": return "bg-yellow-50 border-yellow-200 text-yellow-900";
      case "success": return "bg-green-50 border-green-200 text-green-900";
      case "fail":    return "bg-red-50 border-red-200 text-red-900";
      default:        return "bg-white border-gray-200 text-gray-800";
    }
  };

  // --- Editable Logic for Step 4 (Simplified for brevity) ---
  const startEditingDetail = (key: keyof criteria4Details, field: FieldData) => { setEditingField(key); setTempEditValue(field.value || ""); };
  const cancelEditDetail = () => { setEditingField(null); setTempEditValue(""); };
  const saveDetailEdit = (key: keyof criteria4Details) => { 
    setCriterias(prev => prev.map(criteria => { 
        if (criteria.id === 4 && criteria.ocrResult && criteria.ocrResult.details) { 
            return { ...criteria, ocrResult: { ...criteria.ocrResult, details: { ...criteria.ocrResult.details, [key]: { ...criteria.ocrResult.details[key], value: tempEditValue, isEdited: true } } } }; 
        } 
        return criteria; 
    })); 
    setEditingField(null); 
  };

  // --- Render Functions ---

  // ✅ 1. Render Authority Check (สำหรับ Criteria 2 & 8)
  const renderAuthorityResult = (criteriaId: number, status: criteriaStatus, authority?: AuthorityDetails) => {
    if (!authority) return null;

    // ใช้ status จาก API โดยตรงเพื่อความถูกต้อง (Success = สีเขียว, Fail = สีแดง)
    const isSuccess = status === 'success';
    
    // ใช้ existing getStatusClasses เพื่อความคุมโทนสี
    const statusClass = getStatusClasses(status);

    return (
        <div className="space-y-3 mt-1">
            {/* บรรทัดที่ 1: ผลลัพธ์ (เป็น/ไม่เป็น) พร้อมเครื่องหมาย */}
            <div className={`p-3 rounded border flex items-center gap-3 ${statusClass}`}>
                <div className={`w-20 h-6 rounded-full flex items-center justify-center shrink-0 ${isSuccess ? 'bg-green-200 text-green-800' : 'bg-red-200 text-red-800'}`}>
                    {isSuccess ? "✓ Pass" : "✕ Fail"}
                </div>
                <div className="font-bold text-lg">
                    {authority.result}
                    {criteriaId === 8 && authority.organization && authority.result === "เป็น" && (
                        <span className="ml-2 text-sm font-normal text-gray-600">({authority.organization})</span>
                    )}
                </div>
            </div>

            {/* บรรทัดที่ 2: คำอธิบายเหตุผล */}
            <div className="bg-gray-50 p-3 rounded border border-gray-200 text-sm text-gray-700 leading-relaxed">
                <span className="font-bold text-gray-900 block mb-1">เหตุผล:</span>
                {authority.reason}
            </div>

            {/* บรรทัดที่ 3: อ้างอิงจาก OCR (ถ้ามี) */}
            {authority.evidence && (
                <div className="text-xs text-gray-500 italic pl-3 border-l-4 border-gray-300">
                    "{authority.evidence}"
                </div>
            )}
        </div>
    );
  };

  // 2. Render Step 4 Items (Editable)
  const renderCriteria4Item = (fieldKey: keyof criteria4Details, label: string, field: FieldData | undefined, required: boolean) => {
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
                        <input type="text" className="border border-blue-300 rounded px-2 py-1 text-sm w-full" value={tempEditValue} onChange={(e) => setTempEditValue(e.target.value)} autoFocus />
                        <button onClick={() => saveDetailEdit(fieldKey)} className="text-green-600">✓</button>
                        <button onClick={cancelEditDetail} className="text-red-500">✕</button>
                    </div>
                ) : (
                    <div className="flex items-center gap-2 group-hover/item:bg-gray-50 rounded px-1 -ml-1 transition-colors">
                        {displayValue ? <span className={`font-bold ${field.isEdited ? 'text-gray-900' : 'text-gray-800'}`}>{displayValue}</span> : <span className="text-gray-400 italic">ไม่พบข้อมูล</span>}
                        <button onClick={() => startEditingDetail(fieldKey, field)} className="opacity-0 group-hover/item:opacity-100 text-blue-400">✎</button>
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
      {/* LEFT PANEL: View/Edit Doc (Same as before) */}
      <div className="flex-1 overflow-y-auto p-4 md:p-8 flex justify-center bg-[#f0f2f5]">
        <div className="flex flex-col h-full w-full max-w-[800px] min-h-[1000px] bg-white shadow-sm border border-gray-200 relative">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-white z-10 sticky top-0">
            <div className="flex rounded-full border border-gray-200 overflow-hidden shadow-sm">
                <button onClick={() => setViewMode("pdf")} className={`px-4 py-1.5 text-sm font-medium ${viewMode === "pdf" ? "bg-gray-800 text-white" : "text-gray-600 hover:bg-gray-50"}`}>PDF Original</button>
                <button onClick={() => setViewMode("text")} className={`px-4 py-1.5 text-sm font-medium ${viewMode === "text" ? "bg-gray-800 text-white" : "text-gray-600 hover:bg-gray-50"}`}>Converted Text</button>
            </div>
            {viewMode === "text" && (
                <div className="flex gap-2">
                    {isEditingText ? (
                        <>
                            <button onClick={() => { setDraftText(docText || ""); setIsEditingText(false); }} className="px-3 py-1.5 text-sm text-gray-600 border border-gray-200 rounded">Cancel</button>
                            <button onClick={() => { setDocText(draftText); setIsEditingText(false); }} className="px-3 py-1.5 text-sm text-white bg-green-600 rounded">Done Editing</button>
                        </>
                    ) : (
                        <button onClick={() => { setIsEditingText(true); setDraftText(docText || ""); }} className="px-3 py-1.5 text-sm text-gray-700 border border-gray-200 rounded" disabled={isOCRLoading}>✎ Edit Text</button>
                    )}
                </div>
            )}
          </div>

          <div className="flex-1 relative bg-gray-50">
            {viewMode === "pdf" && (
                 <div className="w-full h-full flex flex-col">
                    {currentFile ? (
                        currentFile.type === 'pdf' ? <iframe src={currentFile.previewUrl} className="w-full h-full border-none" /> : <div className="p-4 flex justify-center"><img src={currentFile.previewUrl} className="max-w-full" /></div>
                    ) : <div className="flex flex-col items-center justify-center h-full text-gray-400"><h2 className="text-xl font-bold">No Document</h2></div>}
                </div>
            )}
            {viewMode === "text" && (
                <div className="w-full h-full bg-white overflow-y-auto p-6 md:p-8 relative">
                    {isOCRLoading && <div className="absolute inset-0 bg-white/80 z-20 flex items-center justify-center"><p className="text-blue-600 animate-pulse">Extracting Text...</p></div>}
                    {isEditingText ? <textarea value={draftText} onChange={(e) => setDraftText(e.target.value)} className="w-full h-full min-h-[500px] border border-gray-200 rounded p-6 font-mono text-sm resize-none" /> : <pre className="whitespace-pre-wrap text-sm font-mono text-gray-800">{docText || "No text content."}</pre>}
                </div>
            )}
          </div>
        </div>
      </div>

      {/* RIGHT PANEL: Checklist */}
      <div className="w-[500px] shrink-0 flex flex-col gap-6 border-l border-gray-200 bg-white p-6 overflow-y-auto">
        {!showChecklist ? (
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold text-[#1e293b] mb-2">เริ่มต้นการตรวจสอบด้วย AI</h2>
              <p className="text-sm text-gray-500 mb-6 leading-relaxed">
                ระบบจะวิเคราะห์ข้อมูลจากข้อความที่แสดง <br/>
                กรุณาตรวจสอบความถูกต้องของข้อความก่อนเริ่มวิเคราะห์
              </p>
              <button onClick={handleStartAnalysis} disabled={isOCRLoading || !currentFile || !docText} className="w-full px-6 py-2 rounded-lg border bg-white text-gray-700 hover:bg-gray-50 transition-all text-sm font-medium shadow-sm">{isOCRLoading ? "Loading Text..." : "Start Analysis"}</button>
            </div>
        ) : (
            <div className="flex h-full flex-col bg-white">
                <div className="space-y-3 pb-4">
                    {criterias.map((criteria) => (
                    <div key={criteria.id}>
                        <div className={`flex items-center justify-between rounded-md border p-4 shadow-sm cursor-pointer transition-all duration-300 ${getStatusClasses(criteria.status)}`} onClick={() => toggleExpand(criteria.id)}>
                          <div className="flex-1 pr-4">
                             <div className="flex items-center gap-2"><span className="text-sm font-medium">{criteria.label}</span></div>
                             {criteria.isProcessing && <span className="inline-flex items-center gap-1 mt-1 text-xs text-blue-600 font-semibold animate-pulse">Processing...</span>}
                             {!expandedCriteriaIds.includes(criteria.id) && !criteria.isProcessing && criteria.status !== 'neutral' && (
                                <div className={`mt-1 text-xs font-bold ${criteria.status === 'success' ? 'text-green-700' : 'text-red-700'}`}>
                                    {/* Show summary result when collapsed */}
                                    {criteria.id === 2 && (criteria.status === 'success' ? 'Result: Pass' : 'Result: Fail')}
                                    {criteria.id === 4 && (criteria.status === 'success' ? 'Result: Pass' : 'Result: Fail')}
                                    {criteria.id === 6 && (criteria.status === 'success' ? 'Result: Pass' : 'Result: Fail')}
                                    {criteria.id === 8 && criteria.ocrResult?.authority && <span>Result: {criteria.ocrResult.authority.result}</span>}
                                </div>
                             )}
                          </div>
                          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform duration-200 ${expandedCriteriaIds.includes(criteria.id) ? 'rotate-180' : ''} opacity-50`}><polyline points="6 9 12 15 18 9"></polyline></svg>
                        </div>

                        {expandedCriteriaIds.includes(criteria.id) && (
                           <div className="mt-2 ml-4 p-4 border-l-2 border-gray-200 bg-gray-50 rounded-r-md">
                              
                              {/* ✅ Criteria 2 & 8: Authority Check UI */}
                              {(criteria.id === 2 || criteria.id === 8) && criteria.ocrResult?.authority && (
                                  renderAuthorityResult(criteria.id, criteria.status, criteria.ocrResult.authority)
                              )}

                              {/* Manual Step UI */}
                              {criteria.type === "manual" && criteria.options && (
                                 <div className="space-y-2">
                                    <p className="text-xs font-bold text-gray-500 mb-2 uppercase">Manual Verification</p>
                                    {criteria.options.map((option) => (
                                      <label key={option.label} className="flex items-center gap-3 cursor-pointer group p-2 rounded hover:bg-white hover:shadow-sm">
                                        <input type="radio" name={`criteria-${criteria.id}`} className="h-4 w-4 text-[#a83b3b]" checked={criteria.selectedOption === option.label} onChange={() => handleOptionSelect(criteria.id, option.label, option.value)} />
                                        <span className="text-sm">{option.label}</span>
                                      </label>
                                    ))}
                                 </div>
                              )}

                              {/* Step 4: Editable Form */}
                              {criteria.id === 4 && criteria.ocrResult?.details && (
                                <div className="space-y-2 bg-white p-2 rounded border border-gray-100">
                                    {renderCriteria4Item("official", "เจ้าหน้าที่ผู้ถูกร้อง", criteria.ocrResult.details.official, true)}
                                    {renderCriteria4Item("entity", "ชื่อหน่วยรับตรวจ", criteria.ocrResult.details.entity, true)}
                                    {renderCriteria4Item("behavior", "พฤติการณ์", criteria.ocrResult.details.behavior, true)}
                                    {renderCriteria4Item("date", "วันเวลา", criteria.ocrResult.details.date, false)}
                                    {renderCriteria4Item("location", "สถานที่", criteria.ocrResult.details.location, false)}
                                </div>
                              )}

                              {/* Step 6: People List */}
                              {criteria.id === 6 && criteria.ocrResult?.people && (
                                <div className="space-y-3">
                                    <div className="bg-white border border-gray-200 rounded-md overflow-hidden">
                                        <div className="bg-gray-100 px-3 py-2 text-xs font-bold text-gray-500 uppercase flex justify-between"><span>Detected People</span><span className="bg-gray-200 text-gray-600 px-1.5 rounded-full">{criteria.ocrResult.people.length}</span></div>
                                        <div className="divide-y divide-gray-100 max-h-60 overflow-y-auto">
                                            {criteria.ocrResult.people.map((person, idx) => (
                                                <div key={idx} className="px-3 py-2 text-sm flex items-center justify-between hover:bg-gray-50">
                                                    <span className="font-medium truncate">{person.name}</span>
                                                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100">{person.role}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                              )}

                              {/* Feedback */}
                              {criteria.ocrResult && (
                                <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-end gap-2">
                                    <span className="text-xs text-gray-400">Is this result correct?</span>
                                    <button onClick={(e) => { e.stopPropagation(); handleFeedback(criteria.id, "up"); }} className={`p-1.5 rounded transition-colors ${criteria.feedback === "up" ? "bg-green-50 text-green-600 ring-1 ring-green-200" : "text-gray-400 hover:text-green-600 hover:bg-gray-50"}`} title="Correct">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2h0a3.13 3.13 0 0 1 3 3.88Z"/></svg>
                                    </button>
                                    <button onClick={(e) => { e.stopPropagation(); handleFeedback(criteria.id, "down"); }} className={`p-1.5 rounded transition-colors ${criteria.feedback === "down" ? "bg-red-50 text-red-600 ring-1 ring-red-200" : "text-gray-400 hover:text-red-600 hover:bg-gray-50"}`} title="Incorrect">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 14V2"/><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22h0a3.13 3.13 0 0 1-3-3.88Z"/></svg>
                                    </button>
                                </div>
                              )}
                           </div>
                        )}
                    </div>
                    ))}
                </div>
                {/* Save Button Area (Same as before) */}
                <div className="pt-4 mt-auto border-t border-gray-100 flex flex-col gap-3">
                    <button onClick={handleSaveToDatabase} disabled={isSaving} className="w-full px-6 py-2 rounded-lg border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 transition-all text-sm font-medium shadow-sm">{isSaving ? "Saving..." : "Save Results"}</button>
                </div>
            </div>
        )}
      </div>
    </div>
  );
}