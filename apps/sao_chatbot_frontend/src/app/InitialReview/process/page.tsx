"use client";

import { useState, useEffect, Suspense, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useInitialReview } from "../InitialReview-context";

import { analyzeDocument } from "../../../libs/initialReview/analyzeDocument";
import { saveAiResult } from "../../../libs/initialReview/saveAIResult";
import { ocrDocument } from "../../../libs/initialReview/callOCR"; 
import { searchAgencyManual } from "../../../libs/initialReview/searchAgency";

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

interface criteria4Details {
  entity: FieldData;
  behavior: FieldData;
  official: FieldData;
  date: FieldData;
  location: FieldData;
}

interface AuthorityDetails {
  aiResult: string;      
  aiReason: string;
  aiOrganization?: string;
  finalResult: string;   
  finalReason: string;   
  finalOrganization?: string; 
  evidence?: string; 
  isVerified: boolean;   
  isOverridden: boolean; 
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
    details?: any; 
    authority?: AuthorityDetails;
    isVerified?: boolean;
  };
}

const initialCriterias: InitialReviewCriteria[] = [
  { id: 1, label: "1. เป็นหน่วยรับตรวจที่อยู่ในสำนักตรวจสอบ", type: "auto", status: "neutral" },
  { id: 2, label: "2. เป็นเรื่องที่อยู่ในหน้าที่ของผู้ว่าการตรวจเงินแผ่นดิน", type: "auto", status: "neutral" },
  { id: 3, label: "3. เป็นเรื่องที่เกิดขึ้นมาแล้วไม่เกิน 5 ปี นับแต่วันที่เกิดเหตุ", type: "manual", status: "pending", options: [{ label: "เกิน", value: "fail" }, { label: "ไม่เกิน", value: "success" }, { label: "ไม่ระบุ", value: "fail" }], selectedOption: null },
  { id: 4, label: "4. เป็นเรื่องที่ระบุรายละเอียดเพียงพอที่จะตรวจสอบได้", type: "auto", status: "neutral", isProcessing: false },
  { id: 5, label: "5. เป็นเรื่องที่ ผตง. หรือผู้ที่ ผตง. มอบหมาย แจ้งผลการตรวจสอบ", type: "manual", status: "pending", options: [{ label: "เคยแจ้ง", value: "fail" }, { label: "ไม่เคยแจ้ง", value: "success" }], selectedOption: null },
  { id: 6, label: "6. รายละเอียดของผู้ร้องเรียน", type: "auto", status: "neutral", isProcessing: false },
  { id: 7, label: "7. ไม่เป็นเรื่องร้องเรียนที่อยู่ระหว่างการดำเนินการของหน่วยงานอื่น", type: "manual", status: "pending", options: [{ label: "เป็น", value: "fail" }, { label: "ไม่เป็น", value: "success" }], selectedOption: null },
  { id: 8, label: "8. เป็นเรื่องร้องเรียนที่อยู่ในอำนาจหน้าที่ขององค์กรอิสระอื่น", type: "auto", status: "neutral" },
];

const INDEPENDENT_ORGS = [
    "ไม่ระบุ / ไม่ทราบ",
    "คณะกรรมการป้องกันและปราบปรามการทุจริตแห่งชาติ (ป.ป.ช.)",
    "คณะกรรมการการเลือกตั้ง (กกต.)",
    "ผู้ตรวจการแผ่นดิน",
    "ศาลปกครอง",
    "ศาลรัฐธรรมนูญ",
    "คณะกรรมการสิทธิมนุษยชนแห่งชาติ (กสม.)"
];

const ROLE_OPTIONS = ["ผู้ร้องเรียน", "ผู้ถูกร้องเรียน", "พยาน", "ผู้เกี่ยวข้อง"];

function InitialReviewProcessContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { currentFile } = useInitialReview();

  const [sessionId, setSessionId] = useState<string | null>(searchParams.get('session_id'));

  const [showChecklist, setShowChecklist] = useState(false);
  const [criterias, setCriterias] = useState<InitialReviewCriteria[]>(initialCriterias);
  const [expandedCriteriaIds, setExpandedCriteriaIds] = useState<number[]>([]);
  const [isSaving, setIsSaving] = useState(false); 
  
  // States for Editing
  const [editingField, setEditingField] = useState<keyof criteria4Details | null>(null);
  const [tempEditValue, setTempEditValue] = useState("");
  const [editingAuthorityReasonId, setEditingAuthorityReasonId] = useState<number | null>(null);
  const [tempAuthorityReason, setTempAuthorityReason] = useState("");
  const [c1SearchQuery, setC1SearchQuery] = useState("");
  const [isC1Searching, setIsC1Searching] = useState(false);

  const [viewMode, setViewMode] = useState<ViewMode>("pdf");
  const [originalText, setOriginalText] = useState<string>(""); 
  const [docText, setDocText] = useState<string>(""); 
  const [draftText, setDraftText] = useState(""); 
  const [isEditingText, setIsEditingText] = useState(false);

  const [isOCRLoading, setIsOCRLoading] = useState(false);
  const [ocrError, setOcrError] = useState<string | null>(null);
  const processedFileIdRef = useRef<string | null>(null);

  useEffect(() => {
      if (sessionId && !docText) {
          setShowChecklist(true);
      }
  }, [sessionId, docText]);

  // --- 1. OCR Logic ---
  useEffect(() => {
    const runOCR = async () => {
        if (!currentFile?.fileObj) return;
        const fileId = currentFile.id || currentFile.name; 
        if (processedFileIdRef.current === fileId) return;
        if (docText) return; 

        processedFileIdRef.current = fileId;
        setIsOCRLoading(true);
        setOcrError(null);
        
        try {
            const result = await ocrDocument(currentFile.fileObj);
            setOriginalText(result.text); 
            setDocText(result.text);
            setDraftText(result.text);
            setViewMode("text");
        } catch (err: any) {
            setOcrError(err.message || "Failed to extract text");
        } finally {
            setIsOCRLoading(false);
        }
    };
    runOCR();
  }, [currentFile, docText]);

  // --- 2. Start Analysis Logic ---
  const handleStartAnalysis = async () => {
    if (!draftText.trim()) { 
        alert("No text to analyze. Please wait for OCR or type manually."); 
        return; 
    }

    setShowChecklist(true);
    setCriterias(prev => prev.map(c => 
        ([1, 2, 4, 6, 8].includes(c.id)) ? { ...c, isProcessing: true } : c
    ));

    try {
        const blob = new Blob([draftText], { type: "text/plain" });
        const fileToAnalyze = new File([blob], `${currentFile?.name || 'doc'}_edited.txt`, { type: "text/plain" });

        const result = await analyzeDocument(fileToAnalyze, sessionId || undefined);

        if (result.status === "success" || result.data) {
            if (result.session_id) {
                setSessionId(result.session_id);
                router.replace(`/InitialReview/process?session_id=${result.session_id}`);
            }

            const { criteria1, criteria2, criteria4, criteria6, criteria8 } = result.data;

            setCriterias(prev => prev.map(c => {
                if (c.id === 1 && criteria1) {
                    let status: criteriaStatus = "pending";
                    let reason = criteria1.reason || "-";
                    let isVerified = false;

                    // ถ้ามี match_count === 1 ให้ auto-select
                    if (criteria1.status === "success" && criteria1.data?.match_count === 1) {
                        status = "success";
                        const h = criteria1.data.hierarchies[0];
                        reason = `พบหน่วยงาน: ${h.department} (${h.ministry})`;
                        criteria1.data.selected_hierarchy = h;
                    } 
                    // ถ้ามาหลายอัน (หรือมาจาก LLM Judge แล้วมีหลายสังกัด) ให้มันค้างรอเลือก
                    else if (criteria1.status === "success" && criteria1.data?.match_count > 1) {
                        status = "pending";
                        reason = `พบหลายสังกัด กรุณาเลือก`;
                        criteria1.data.selected_hierarchy = null; // ล้างค่าเผื่อไว้
                    } 
                    else if (criteria1.status === "fail") {
                        status = "fail";
                    }

                    return { ...c, isProcessing: false, status: status, ocrResult: { status: criteria1.status, title: "หน่วยรับตรวจ", reason: reason, details: criteria1, isVerified: isVerified } };
                }

                if (c.id === 2 && criteria2) {
                    return { ...c, isProcessing: false, status: criteria2.status, ocrResult: { status: criteria2.status, title: criteria2.title, reason: criteria2.reason, authority: { aiResult: criteria2.result, aiReason: criteria2.reason, finalResult: criteria2.result, finalReason: criteria2.reason, evidence: criteria2.evidence, isVerified: false, isOverridden: false } } };
                }

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

                if (c.id === 6 && criteria6) {
                    return { ...c, isProcessing: false, status: criteria6.status, ocrResult: { status: criteria6.status, title: criteria6.title, reason: criteria6.reason, people: criteria6.people || [] } };
                }

                if (c.id === 8 && criteria8) {
                    return { ...c, isProcessing: false, status: criteria8.status, ocrResult: { status: criteria8.status, title: criteria8.title, reason: criteria8.reason, authority: { aiResult: criteria8.result, aiReason: criteria8.reason, aiOrganization: criteria8.organization, finalResult: criteria8.result, finalReason: criteria8.reason, finalOrganization: criteria8.organization || INDEPENDENT_ORGS[0], evidence: criteria8.evidence, isVerified: false, isOverridden: false } } };
                }

                return c;
            }));
            
            setExpandedCriteriaIds([1, 2, 3, 4, 5, 6, 7, 8]);
        } else {
            throw new Error(result.message || "Unknown error");
        }
    } catch (error: any) {
        console.error(error);
        setCriterias(prev => prev.map(s => ({...s, isProcessing: false})));
        alert("Analysis Failed: " + error.message);
    }
  };

  const handleC1HierarchySelect = (criteriaId: number, hierarchy: any) => {
    setCriterias(prev => prev.map(c => {
        if (c.id === criteriaId && c.ocrResult?.details?.data) {
            return {
                ...c,
                status: 'success', 
                ocrResult: {
                    ...c.ocrResult,
                    status: 'success',
                    reason: `พบหน่วยงาน: ${hierarchy.department} (${hierarchy.ministry})`,
                    isVerified: false,
                    details: {
                        ...c.ocrResult.details,
                        data: {
                            ...c.ocrResult.details.data,
                            selected_hierarchy: hierarchy 
                        }
                    }
                }
            };
        }
        return c;
    }));
  };

  const handleC1ManualSearch = async () => {
      if (!c1SearchQuery.trim()) return;
      setIsC1Searching(true);
      
      try {
          const result = await searchAgencyManual(c1SearchQuery);
          
          setCriterias(prev => prev.map(c => {
              if (c.id === 1) {
                  let status: criteriaStatus = "pending";
                  let reason = result.reason || "-";
                  let isVerified = false;

                  if (result.status === "success" && result.data?.match_count === 1) {
                      status = "success";
                      const h = result.data.hierarchies[0];
                      reason = `ค้นพบด้วยตนเอง: ${h.department} (${h.ministry})`;
                      result.data.selected_hierarchy = h;
                  } else if (result.status === "success" && result.data?.match_count > 1) {
                      status = "pending";
                      reason = `ค้นพบหลายสังกัด กรุณาเลือก`;
                      result.data.selected_hierarchy = null;
                  } else if (result.status === "fail" || result.status === "pending_llm") {
                      // ถ้ายังไม่ชัวร์ ให้ถือว่า fail ในมุมของการค้นหา manual
                      status = "fail";
                      reason = result.status === "pending_llm" ? "พบตัวเลือกที่คล้ายคลึง แต่ต้องใช้ AI ตัดสิน (กรุณาพิมพ์ให้ชัดเจนกว่านี้)" : result.reason;
                  }

                  return { ...c, status: status, ocrResult: { status: result.status, title: "หน่วยรับตรวจ (Manual)", reason: reason, details: result, isVerified: isVerified } };
              }
              return c;
          }));

      } catch (error) {
          alert("ค้นหาไม่สำเร็จ กรุณาลองใหม่");
      } finally {
          setIsC1Searching(false);
          setC1SearchQuery("");
      }
  };

  const handleVerifyProcess = (id: number) => {
    setCriterias(prev => prev.map(c => {
        if (c.id === id && c.ocrResult) {
            if (id === 1) {
                return { ...c, ocrResult: { ...c.ocrResult, isVerified: true } };
            }
            if ((id === 2 || id === 8) && c.ocrResult.authority) {
                return { ...c, ocrResult: { ...c.ocrResult, authority: { ...c.ocrResult.authority, isVerified: true } } };
            }
        }
        return c;
    }));
  };

  const handleUpdatePerson = (idx: number, field: 'name' | 'role', value: string) => {
      setCriterias(prev => prev.map(c => {
          if (c.id === 6 && c.ocrResult?.people) {
              const newPeople = [...c.ocrResult.people];
              newPeople[idx] = { ...newPeople[idx], [field]: value };
              return { ...c, status: 'success', ocrResult: { ...c.ocrResult, people: newPeople } };
          }
          return c;
      }));
  };

  const handleRemovePerson = (idx: number) => {
      setCriterias(prev => prev.map(c => {
          if (c.id === 6 && c.ocrResult?.people) {
              const newPeople = c.ocrResult.people.filter((_, i) => i !== idx);
              return { ...c, status: newPeople.length > 0 ? 'success' : 'fail', ocrResult: { ...c.ocrResult, people: newPeople } };
          }
          return c;
      }));
  };

  const handleAddPerson = () => {
      setCriterias(prev => prev.map(c => {
          if (c.id === 6) {
              const currentPeople = c.ocrResult?.people || [];
              const newPeople = [...currentPeople, { name: "", role: "ผู้ร้องเรียน" }];
              return { ...c, status: 'success', ocrResult: { ...(c.ocrResult as any), status: 'success', people: newPeople } };
          }
          return c;
      }));
  };

  // --- 3. Save Logic ---
  const handleSaveToDatabase = async () => {
    if (!sessionId) {
      alert("Error: ไม่มี Session ID กรุณากดปุ่ม Start Analysis ก่อนครับ");
      return;
    }

    // บังคับกดยืนยันข้อ 1 (ถ้ามีผลลัพธ์), 2, และ 8
    const unverifiedC1 = criterias.filter(c => c.id === 1 && c.ocrResult?.status === 'success' && !c.ocrResult?.isVerified);
    const unverifiedAuto = criterias.filter(c => (c.id === 2 || c.id === 8) && c.ocrResult?.authority && !c.ocrResult.authority.isVerified);
    const unverifiedManual = criterias.filter(c => (c.id === 3 || c.id === 5 || c.id === 7) && !c.selectedOption);

    if (unverifiedC1.length > 0 || unverifiedAuto.length > 0 || unverifiedManual.length > 0) {
        const missingIds = [
            ...unverifiedC1.map(c => c.id),
            ...unverifiedAuto.map(c => c.id),
            ...unverifiedManual.map(c => c.id)
        ].sort((a, b) => a - b);
        
        setExpandedCriteriaIds(prev => [...new Set([...prev, ...missingIds])]);
        alert(`⚠️ ไม่สามารถบันทึกได้!\n\nกรุณาตรวจสอบและยืนยันผลให้ครบถ้วน\n\nข้อที่ยังขาดอยู่คือ: ข้อ ${missingIds.join(", ")}`);
        return; 
    }

    setIsSaving(true);
    try {
      await saveAiResult({
          session_id: sessionId,
          criteria_id: 0, 
          result: {
              original_text: originalText,
              edited_text: docText
          }
      });

      const criteriasToSave = criterias.filter(s => s.ocrResult || s.status !== 'neutral' || s.selectedOption);
      for (const criteria of criteriasToSave) {
          let resultData = criteria.ocrResult || {};
          
          if ((criteria.id === 2 || criteria.id === 8) && criteria.ocrResult?.authority) {
              const auth = criteria.ocrResult.authority;
              resultData = {
                  ...resultData,
                  status: criteria.status,
                  reason: auth.finalReason,
                  authority: {
                      ...auth,
                      result: auth.finalResult,
                      reason: auth.finalReason,
                      organization: auth.finalOrganization
                  }
              };
          }

          if(criteria.type === 'manual') {
             resultData = { ...resultData, manual_selection: criteria.selectedOption, status: criteria.status };
          }

          await saveAiResult({
              session_id: sessionId,
              criteria_id: criteria.id,
              result: resultData,
              feedback: criteria.feedback
          });
      }
    } catch (error: any) {
      console.error("Save Error:", error);
      alert("เกิดข้อผิดพลาดในการบันทึก: " + error.message);
    } finally {
      setIsSaving(false);
    }
    if (!sessionId) {
        console.error("sessionId is undefined");
    return;
    }
    router.push(`/InitialReview/${sessionId}`);
  };

  const toggleExpand = (id: number) => {
    setExpandedCriteriaIds(prev => prev.includes(id) ? prev.filter(cId => cId !== id) : [...prev, id]);
  };

  const toggleExpandAll = () => {
    if (expandedCriteriaIds.length === criterias.length) {
      setExpandedCriteriaIds([]); 
    } else {
      setExpandedCriteriaIds(criterias.map(c => c.id)); 
    }
  };

  const handleOptionSelect = (criteriaId: number, optionLabel: string, resultStatus: "success" | "fail") => {
    setCriterias(prev => prev.map(criteria => criteria.id === criteriaId ? { ...criteria, status: resultStatus as any, selectedOption: optionLabel } : criteria));
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

  const handleAuthorityResultToggle = (id: number) => {
    setCriterias(prev => prev.map(c => {
        if (c.id === id && c.ocrResult?.authority) {
            const currentRes = c.ocrResult.authority.finalResult;
            const newRes = currentRes === "เป็น" ? "ไม่เป็น" : "เป็น";
            const isOverridden = newRes !== c.ocrResult.authority.aiResult;
            
            let newStatus: criteriaStatus = 'pending';
            if (id === 2) newStatus = newRes === "เป็น" ? 'success' : 'fail';
            if (id === 8) newStatus = newRes === "ไม่เป็น" ? 'success' : 'fail'; 

            return { ...c, status: newStatus, ocrResult: { ...c.ocrResult, status: newStatus as any, authority: { ...c.ocrResult.authority, finalResult: newRes, isOverridden: isOverridden, isVerified: false } } };
        }
        return c;
    }));
  };

  const handleAuthorityOrgChange = (id: number, newOrg: string) => {
    setCriterias(prev => prev.map(c => {
        if (c.id === id && c.ocrResult?.authority) {
            return { ...c, ocrResult: { ...c.ocrResult, authority: { ...c.ocrResult.authority, finalOrganization: newOrg, isVerified: false } } };
        }
        return c;
    }));
  };

  const startEditingAuthorityReason = (id: number, currentReason: string) => {
      setEditingAuthorityReasonId(id);
      setTempAuthorityReason(currentReason);
  };

  const saveAuthorityReason = (id: number) => {
    setCriterias(prev => prev.map(c => {
        if (c.id === id && c.ocrResult?.authority) {
            return { ...c, ocrResult: { ...c.ocrResult, authority: { ...c.ocrResult.authority, finalReason: tempAuthorityReason, isVerified: false } } };
        }
        return c;
    }));
    setEditingAuthorityReasonId(null);
  };

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

  const renderAuthorityHITL = (criteriaId: number, status: criteriaStatus, authority: AuthorityDetails) => {
    const isSuccess = status === 'success';
    const statusClass = getStatusClasses(status);
    let statusLabel = isSuccess ? "Pass" : "Fail";
    if (criteriaId === 2) statusLabel = isSuccess ? "อยู่ในอำนาจ สตง." : "ไม่อยู่ในอำนาจ";
    if (criteriaId === 8) statusLabel = isSuccess ? "ไม่อยู่ในอำนาจอิสระอื่น" : "อยู่ในอำนาจอิสระอื่น";
    const isEditingReason = editingAuthorityReasonId === criteriaId;

    return (
        <div className="space-y-4 mt-1">
            <div className="flex items-center justify-between text-xs mb-1">
                 <div className="flex items-center gap-1 text-gray-500">
                    <span className="font-semibold">🤖 AI Suggestion:</span>
                    <span>{authority.aiResult}</span>
                 </div>
                 <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full border ${authority.isVerified ? 'bg-green-100 text-green-700 border-green-200' : 'bg-yellow-50 text-yellow-700 border-yellow-200'}`}>
                    {authority.isVerified ? <span>✓ Verified by Human</span> : <span>⚠️ Pending Review</span>}
                 </div>
            </div>

            <div className={`p-4 rounded-lg border-2 flex flex-col gap-3 transition-colors ${authority.isOverridden ? 'border-orange-200 bg-orange-50' : (isSuccess ? 'border-green-100 bg-green-50' : 'border-red-100 bg-red-50')}`}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <button 
                            onClick={(e) => { e.stopPropagation(); handleAuthorityResultToggle(criteriaId); }}
                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${isSuccess ? 'bg-green-500' : 'bg-red-500'}`}
                        >
                            <span className={`${isSuccess ? 'translate-x-6' : 'translate-x-1'} inline-block h-4 w-4 transform rounded-full bg-white transition-transform`} />
                        </button>
                        <div>
                            <div className="text-sm font-bold text-gray-800">{authority.finalResult}</div>
                            <div className="text-xs text-gray-500">{statusLabel}</div>
                        </div>
                    </div>
                    {authority.isOverridden && <span className="text-xs font-bold text-orange-600 bg-white px-2 py-1 rounded border border-orange-200">Manual Override</span>}
                </div>
            </div>

            {criteriaId === 8 && authority.finalResult === "เป็น" && (
                <div className="bg-white p-3 rounded border border-gray-200 shadow-sm">
                    <label className="block text-xs font-bold text-gray-600 mb-1">องค์กรที่รับผิดชอบ (AI: {authority.aiOrganization || "-"})</label>
                    <select 
                        className="w-full text-sm border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500"
                        value={authority.finalOrganization || ""}
                        onChange={(e) => handleAuthorityOrgChange(criteriaId, e.target.value)}
                    >
                        {INDEPENDENT_ORGS.map(org => (
                            <option key={org} value={org}>{org}</option>
                        ))}
                    </select>
                </div>
            )}

            <div className="bg-white p-3 rounded border border-gray-200 shadow-sm group">
                <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-gray-900 text-sm">เหตุผลประกอบ:</span>
                    {!isEditingReason && (
                        <button onClick={() => startEditingAuthorityReason(criteriaId, authority.finalReason)} className="text-xs text-blue-500 hover:underline flex items-center gap-1">
                            ✎ แก้ไข
                        </button>
                    )}
                </div>
                
                {isEditingReason ? (
                    <div className="flex flex-col gap-2">
                        <textarea 
                            className="w-full text-sm p-2 border border-blue-300 rounded focus:ring-1 focus:ring-blue-500 min-h-[80px]"
                            value={tempAuthorityReason}
                            onChange={(e) => setTempAuthorityReason(e.target.value)}
                            autoFocus
                        />
                        <div className="flex justify-end gap-2">
                            <button onClick={() => setEditingAuthorityReasonId(null)} className="px-3 py-1 text-xs text-gray-600 hover:bg-gray-100 rounded">Cancel</button>
                            <button onClick={() => saveAuthorityReason(criteriaId)} className="px-3 py-1 text-xs text-white bg-blue-600 hover:bg-blue-700 rounded">Save</button>
                        </div>
                    </div>
                ) : (
                    <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{authority.finalReason}</p>
                )}
            </div>

            {authority.evidence && (
                <div className="text-xs text-gray-500 italic pl-3 border-l-4 border-gray-300">
                    หลักฐานจากเอกสาร: "{authority.evidence}"
                </div>
            )}

            {!authority.isVerified && (
                <button 
                    onClick={() => handleVerifyProcess(criteriaId)}
                    className="w-full mt-2 py-2 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors shadow-sm"
                >
                    <span>✓ ยืนยันผลการตรวจสอบ</span>
                </button>
            )}
        </div>
    );
  };

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
    <div className="flex h-full w-full flex-row overflow-hidden bg-[#f9fafb] text-gray-800">
      {/* LEFT PANEL: View/Edit Doc */}
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
                    {isEditingText ? <textarea value={draftText} onChange={(e) => setDraftText(e.target.value)} className="w-full h-full min-h-[500px] border border-gray-200 rounded p-6 font-mono text-sm resize-none" /> : <pre className="whitespace-pre-wrap text-sm font-mono text-gray-900">{docText || "No text content."}</pre>}
                </div>
            )}
          </div>
        </div>
      </div>

      {/* RIGHT PANEL: Checklist */}
      <div className="w-[500px] shrink-0 flex flex-col gap-6 border-l border-gray-200 bg-white text-gray-800 p-6 overflow-y-auto">
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
                {sessionId && (
                    <div className="mb-4 p-2 bg-blue-50 border border-blue-100 rounded text-xs text-blue-600 font-mono">
                        Session: {sessionId}
                    </div>
                )}
                
                <div className="space-y-3 pb-4">
                    {criterias.map((criteria) => (
                    <div key={criteria.id}>
                        <div className={`flex items-center justify-between rounded-md border p-4 shadow-sm cursor-pointer transition-all duration-300 ${getStatusClasses(criteria.status)}`} onClick={() => toggleExpand(criteria.id)}>
                          <div className="flex-1 pr-4">
                             <div className="flex items-center gap-2"><span className="text-sm font-medium">{criteria.label}</span></div>
                             {criteria.isProcessing && <span className="inline-flex items-center gap-1 mt-1 text-xs text-blue-600 font-semibold animate-pulse">Processing...</span>}
                             
                             {!expandedCriteriaIds.includes(criteria.id) && !criteria.isProcessing && criteria.status !== 'neutral' && (
                                <div className={`mt-1 text-xs font-bold ${criteria.status === 'success' ? 'text-green-700' : 'text-red-700'}`}>
                                    {criteria.type === "auto" && criteria.id === 1 && (criteria.status === 'success' ? 'Result: Pass' : (criteria.status === 'pending' ? 'Result: Pending' : 'Result: Fail'))}
                                    {criteria.type === "auto" && criteria.id === 2 && (criteria.status === 'success' ? 'Result: Pass' : 'Result: Fail')}
                                    {criteria.type === "auto" && criteria.id === 4 && (criteria.status === 'success' ? 'Result: Pass' : 'Result: Fail')}
                                    {criteria.type === "auto" && criteria.id === 6 && (criteria.status === 'success' ? 'Result: Pass' : 'Result: Fail')}
                                    {criteria.type === "auto" && criteria.id === 8 && (criteria.status === 'success' ? 'Result: Pass' : 'Result: Fail')}
                                    
                                    {criteria.type === "manual" && criteria.selectedOption && `Result: ${criteria.selectedOption}`}
                                </div>
                             )}
                          </div>
                          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform duration-200 ${expandedCriteriaIds.includes(criteria.id) ? 'rotate-180' : ''} opacity-50`}><polyline points="6 9 12 15 18 9"></polyline></svg>
                        </div>

                        {expandedCriteriaIds.includes(criteria.id) && (
                           <div className="mt-2 ml-4 p-4 border-l-2 border-gray-200 bg-gray-50 rounded-r-md">
                              {criteria.id === 1 && criteria.ocrResult?.details && (
                                <div className="space-y-3">
                                    <div className="text-sm font-bold text-gray-800 flex justify-between items-center">
                                        <span>ชื่อที่ตรวจพบ: <span className="text-blue-600">{criteria.ocrResult.details.data?.agency_name || "ไม่ระบุ"}</span></span>
                                        {criteria.ocrResult.isVerified ? (
                                            <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">✓ Verified</span>
                                        ) : (
                                            <span className="text-xs bg-yellow-50 text-yellow-700 px-2 py-0.5 rounded-full border border-yellow-200">⚠️ Pending Review</span>
                                        )}
                                    </div>
                                    {criteria.ocrResult.details.data?.selected_hierarchy ? (
                                        <div className={`p-4 rounded-md mt-2 shadow-sm border transition-colors ${criteria.ocrResult.isVerified ? 'bg-green-50 border-green-200' : 'bg-white border-blue-200'}`}>
                                            <div className="text-xs font-semibold mb-3 border-b pb-2 text-gray-700">ข้อมูลหน่วยรับตรวจที่ยืนยันแล้ว</div>
                                            <div className="grid grid-cols-1 gap-2 text-xs text-gray-700">
                                                <div className="flex justify-between"><span className="font-semibold w-1/3">ชื่อหน่วยงาน:</span> <span className="w-2/3">{criteria.ocrResult.details.data.agency_name}</span></div>
                                                <div className="flex justify-between"><span className="font-semibold w-1/3">ชื่อสังกัด:</span> <span className="w-2/3">{criteria.ocrResult.details.data.selected_hierarchy.department}</span></div>
                                                <div className="flex justify-between"><span className="font-semibold w-1/3">ชื่อกระทรวง:</span> <span className="w-2/3">{criteria.ocrResult.details.data.selected_hierarchy.ministry}</span></div>
                                            </div>
                                            
                                            {!criteria.ocrResult.isVerified && (
                                                <button 
                                                    onClick={() => handleVerifyProcess(criteria.id)}
                                                    className="w-full mt-4 py-2 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors shadow-sm"
                                                >
                                                    <span>✓ ยืนยันข้อมูลนี้ถูกต้อง</span>
                                                </button>
                                            )}
                                        </div>
                                    ) : (
                                        <>
                                            <p className="text-sm text-gray-600">{criteria.ocrResult.reason}</p>
                                            {criteria.status === "pending" && criteria.ocrResult.details.data?.hierarchies && (
                                                <div className="mt-3">
                                                    <label className="block text-xs font-bold text-gray-500 mb-2">
                                                        กรุณาเลือกสังกัดที่ถูกต้อง <span className="text-red-500">*จำเป็น</span>
                                                    </label>
                                                    <div className="space-y-2">
                                                        {criteria.ocrResult.details.data.hierarchies.map((h: any, idx: number) => (
                                                            <label key={idx} className="flex items-start gap-3 p-3 border rounded-lg bg-white cursor-pointer hover:bg-blue-50 hover:border-blue-200 transition-colors">
                                                                <input 
                                                                    type="radio" 
                                                                    name="c1_hierarchy" 
                                                                    className="mt-1 h-4 w-4 text-blue-600"
                                                                    onChange={() => handleC1HierarchySelect(criteria.id, h)}
                                                                />
                                                                <div className="text-sm flex-1">
                                                                    <div className="font-bold text-gray-800">{h.department} 
                                                                    </div>
                                                                    <div className="text-xs text-gray-500 mt-1">{h.ministry}  
                                                                    </div>
                                                                </div>
                                                            </label>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </>
                                    )}

                                    <div className="mt-4 pt-4 border-t border-gray-200">
                                        <label className="block text-xs font-bold text-gray-500 mb-1">ค้นหาหน่วยงานด้วยตนเอง (กรณี AI หาไม่เจอ)</label>
                                        <div className="flex gap-2">
                                            <input 
                                                type="text" 
                                                placeholder="พิมพ์ชื่อโรงเรียน, เทศบาล ฯลฯ"
                                                className="flex-1 text-sm border border-gray-300 rounded px-3 py-1.5 focus:ring-1 focus:ring-blue-500"
                                                value={c1SearchQuery}
                                                onChange={(e) => setC1SearchQuery(e.target.value)}
                                                onKeyDown={(e) => e.key === 'Enter' && handleC1ManualSearch()}
                                            />
                                            <button 
                                                onClick={handleC1ManualSearch}
                                                disabled={isC1Searching}
                                                className="bg-gray-800 hover:bg-gray-900 text-white px-3 py-1.5 rounded text-sm font-medium disabled:opacity-50"
                                            >
                                                {isC1Searching ? "..." : "ค้นหา"}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                              )}

                              {(criteria.id === 2 || criteria.id === 8) && criteria.ocrResult?.authority && (
                                  renderAuthorityHITL(criteria.id, criteria.status, criteria.ocrResult.authority)
                              )}

                              {criteria.type === "manual" && criteria.options && (
                                 <div className="space-y-2">
                                    <p className="text-xs font-bold text-gray-500 mb-2 uppercase">Manual Verification <span className="text-red-500">*จำเป็น</span></p>
                                    {criteria.options.map((option) => (
                                      <label key={option.label} className={`flex items-center gap-3 cursor-pointer group p-2 rounded hover:shadow-sm border ${criteria.selectedOption === option.label ? 'bg-blue-50 border-blue-200' : 'bg-white border-transparent hover:border-gray-200'}`}>
                                        <input type="radio" name={`criteria-${criteria.id}`} className="h-4 w-4 text-blue-600" checked={criteria.selectedOption === option.label} onChange={() => handleOptionSelect(criteria.id, option.label, option.value as "success"|"fail")} />
                                        <span className="text-sm">{option.label}</span>
                                      </label>
                                    ))}
                                 </div>
                              )}

                              {criteria.id === 4 && criteria.ocrResult?.details && (
                                <div className="space-y-2 bg-white p-2 rounded border border-gray-100">
                                    {renderCriteria4Item("official", "เจ้าหน้าที่ผู้ถูกร้อง", criteria.ocrResult.details.official, true)}
                                    {renderCriteria4Item("entity", "ชื่อหน่วยรับตรวจ", criteria.ocrResult.details.entity, true)}
                                    {renderCriteria4Item("behavior", "พฤติการณ์", criteria.ocrResult.details.behavior, true)}
                                    {renderCriteria4Item("date", "วันเวลา", criteria.ocrResult.details.date, false)}
                                    {renderCriteria4Item("location", "สถานที่", criteria.ocrResult.details.location, false)}
                                </div>
                              )}
                              {criteria.id === 6 && criteria.ocrResult?.people && (
                                <div className="space-y-3">
                                    <div className="bg-white border border-gray-200 rounded-md overflow-hidden p-3">
                                        <div className="flex justify-between items-center mb-3">
                                            <span className="text-xs font-bold text-gray-500 uppercase">รายชื่อบุคคลที่พบ</span>
                                        </div>
                                        
                                        <div className="space-y-2">
                                            {criteria.ocrResult.people.length === 0 ? (
                                                <div className="text-sm text-gray-400 text-center py-4">ไม่พบรายชื่อบุคคล</div>
                                            ) : (
                                                criteria.ocrResult.people.map((person, idx) => (
                                                    <div key={idx} className="flex gap-2 items-center bg-gray-50 p-2 rounded border border-gray-100">
                                                        <input 
                                                            type="text" 
                                                            value={person.name} 
                                                            onChange={(e) => handleUpdatePerson(idx, 'name', e.target.value)}
                                                            className="flex-1 text-sm border border-gray-300 rounded px-2 py-1"
                                                            placeholder="ชื่อ-นามสกุล"
                                                        />
                                                        <select 
                                                            value={person.role} 
                                                            onChange={(e) => handleUpdatePerson(idx, 'role', e.target.value)}
                                                            className="text-sm border border-gray-300 rounded px-2 py-1 bg-white"
                                                        >
                                                            {ROLE_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                                                        </select>
                                                        <button 
                                                            onClick={() => handleRemovePerson(idx)}
                                                            className="text-red-500 hover:text-red-700 p-1"
                                                            title="ลบ"
                                                        >
                                                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
                                                        </button>
                                                    </div>
                                                ))
                                            )}
                                        </div>
                                        
                                        <button 
                                            onClick={handleAddPerson}
                                            className="mt-3 w-full border border-dashed border-gray-300 text-gray-500 hover:border-blue-400 hover:text-blue-600 text-xs font-semibold py-2 rounded transition-colors"
                                        >
                                            + เพิ่มรายชื่อบุคคล
                                        </button>
                                    </div>
                                </div>
                              )}

                              {criteria.ocrResult && !(criteria.id === 2 || criteria.id === 8) && !(criteria.id === 1) && (
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
                
                <div className="pt-4 mt-auto border-t border-gray-100 flex flex-col gap-3">
                    <button onClick={toggleExpandAll} className="w-full px-6 py-2 rounded-lg border border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100 transition-all text-sm font-medium shadow-sm">
                        {expandedCriteriaIds.length === criterias.length ? "ย่อ Criteria ทั้งหมด" : "ขยาย Criteria ทั้งหมด"}
                    </button>
                    <button onClick={handleSaveToDatabase} disabled={isSaving || !sessionId} className="w-full px-6 py-2 rounded-lg border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 transition-all text-sm font-medium shadow-sm disabled:opacity-50">
                        {isSaving ? "Saving..." : "สรุปผลและบันทึกข้อมูล"}
                    </button>
                </div>
            </div>
        )}
      </div>
    </div>
  );
}

export default function InitialReviewProjectPage() {
  return (
    <Suspense fallback={<div className="flex h-screen w-full items-center justify-center text-gray-500 font-medium">กำลังโหลดข้อมูล...</div>}>
      <InitialReviewProcessContent />
    </Suspense>
  );
}