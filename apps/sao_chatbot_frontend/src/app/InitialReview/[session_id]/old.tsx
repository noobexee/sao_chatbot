"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getReviewSummary, ReviewSummaryData } from "../../../libs/InitialReview/getSummaray";

// ─────────────────────────────────────────────────────────────────────────────
// Print CSS
//
// Uses visibility:hidden on body + visibility:visible on #print-area.
// This works at ANY DOM nesting depth (Next.js layouts, portals, etc.)
// because visibility is inherited — children of a hidden element can
// still be made visible, unlike display:none.
//
// position:fixed on #print-area pulls it out of the scrollable container
// so the browser renders the full content, not just the visible viewport.
// ─────────────────────────────────────────────────────────────────────────────
const PRINT_CSS = `
@media print {
  @page { size: A4 portrait; margin: 12mm 14mm; }

  /*
    Step 1: hide everything via visibility (works at any nesting depth,
    children can still override it — unlike display:none).
  */
  .no-print     { display: none !important; }
  body          { visibility: hidden !important; }
  #print-area   { visibility: visible !important; }
  #print-area * { visibility: visible !important; }

  /*
    Step 2: every ancestor between <body> and #print-area that has
    overflow:hidden/auto/scroll will clip the printed output.
    We must reset ALL of them. We target by id where possible,
    and use the wildcard for any unknown Next.js wrappers.
    height:auto + overflow:visible lets content flow across pages.
  */
  html, body,
  #__next,
  #scroll-wrapper,
  body > div,
  body > div > div {
    overflow: visible !important;
    height: auto !important;
    max-height: none !important;
  }

  /*
    Step 3: #print-area itself — no position tricks, just natural flow.
    width:100% fills the @page content area set above.
  */
  #print-area {
    position: static !important;
    display: block !important;
    width: 100% !important;
    height: auto !important;
    max-height: none !important;
    overflow: visible !important;
    padding: 0 !important;
    margin: 0 !important;
    box-shadow: none !important;
    background: white !important;
    font-size: 8.5pt !important;
    box-sizing: border-box !important;
  }

  /* Compact spacing */
  #print-area .pf    { margin-bottom: 3pt !important; }
  #print-area .pdiv  { margin: 5pt 0 4pt !important; border-top-color: #999 !important; }
  #print-area .ptdiv { margin: 3pt 0 !important; border-top-color: #ccc !important; }
  #print-area .psh   { padding: 2pt 6pt !important; margin-bottom: 3pt !important; font-size: 8pt !important; }
  #print-area .pcb   { padding: 4pt 8pt !important; margin-bottom: 4pt !important; border-color: #aaa !important; }
  #print-area textarea,
  #print-area input[type=text] {
    font-size: 8pt !important; padding: 1pt 3pt !important;
    background: transparent !important; border-color: #aaa !important;
    resize: none !important;
  }
  #print-area .pgap { gap: 2pt 12pt !important; }
  #print-area .psub { padding-left: 8pt !important; border-left-color: #ccc !important; }
  #print-area .page-break { page-break-before: always !important; display: block !important; }
}
`;

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────
interface FormState {
  ocr_text: string;
  c1: boolean | null;
  c2: boolean | null;
  c3: boolean | null;
  c4: (boolean | null)[];
  c5: boolean | null;
  c6: (boolean | null)[];
  c7_no: boolean;
  c7_yes: boolean;
  c7_reason: string;
  c8_true: boolean;
  c8_true_reason: string;
  c8_false: boolean;
  c8_false_reason: string;
  conclusion_accept: boolean;
  conclusion_accept_topic: string;
  conclusion_reject: boolean;
  conclusion_reject_topic: string;
  conclusion_reject_reason: string;
  conclusion_reject_notify: boolean;
  conclusion_art21: boolean;
  conclusion_art21_topic_12: string;
  conclusion_art21_topic_3: string;
  conclusion_art21_notify: boolean;
  conclusion_other: boolean;
  conclusion_other_text: string;
}

function buildFormState(s: ReviewSummaryData): FormState {
  const c7_no    = s.criteria_7 != null && "true"  in s.criteria_7;
  const c7_yes   = s.criteria_7 != null && "false" in s.criteria_7;
  const c8_false = s.criteria_8 != null && "false" in s.criteria_8;
  const c8_true  = s.criteria_8 != null && "true"  in s.criteria_8;
  return {
    ocr_text: s.OCR_text ?? "",
    c1: s.criteria_1 ?? null,
    c2: s.criteria_2 ?? null,
    c3: s.criteria_3 ?? null,
    c4: s.criteria_4 ?? [null, null, null, null],
    c5: s.criteria_5 ?? null,
    c6: s.criteria_6 ?? [null, null, null],
    c7_no, c7_yes,
    c7_reason: c7_yes ? ((s.criteria_7 as Record<string, string>)["false"] ?? "") : "",
    c8_true, c8_false,
    c8_true_reason:  c8_true  ? ((s.criteria_8 as Record<string, string>)["true"]  ?? "") : "",
    c8_false_reason: c8_false ? ((s.criteria_8 as Record<string, string>)["false"] ?? "") : "",
    conclusion_accept: false, conclusion_accept_topic: "",
    conclusion_reject: false, conclusion_reject_topic: "",
    conclusion_reject_reason: "", conclusion_reject_notify: false,
    conclusion_art21: false, conclusion_art21_topic_12: "",
    conclusion_art21_topic_3: "", conclusion_art21_notify: false,
    conclusion_other: false, conclusion_other_text: "",
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Shared styles
// ─────────────────────────────────────────────────────────────────────────────
const font: React.CSSProperties = { fontFamily: "'Sarabun', sans-serif" };

const inputSt: React.CSSProperties = {
  ...font, width: "100%", fontSize: 12, color: "#1a1a2e",
  border: "1px solid #c8cfd8", borderRadius: 3,
  padding: "4px 7px", background: "#fafbfc",
  resize: "vertical", outline: "none", boxSizing: "border-box",
};

// ─────────────────────────────────────────────────────────────────────────────
// Micro-components
// ─────────────────────────────────────────────────────────────────────────────
function Div({ thin }: { thin?: boolean }) {
  return (
    <hr className={thin ? "ptdiv" : "pdiv"} style={{
      border: "none",
      borderTop: thin ? "1px solid #e8eaed" : "1px solid #c5ccd4",
      margin: thin ? "7px 0" : "11px 0 9px",
    }} />
  );
}

function SHdr({ children, sub }: { children: React.ReactNode; sub?: boolean }) {
  return (
    <div className="psh" style={{
      fontWeight: 700, fontSize: sub ? 11 : 12, color: "#1e3a52",
      padding: "3px 8px", marginBottom: 7,
      background: sub ? "#f4f6f8" : "#edf1f5",
      borderLeft: `3px solid ${sub ? "#5a8aaa" : "#1e3a52"}`,
    }}>
      {children}
    </div>
  );
}

function FL({ children }: { children: React.ReactNode }) {
  return (
    <label style={{ display: "block", fontWeight: 600, fontSize: 11.5, color: "#333", marginBottom: 2 }}>
      {children}
    </label>
  );
}

function CB({ checked, onChange, children, top }: {
  checked: boolean; onChange: (v: boolean) => void;
  children: React.ReactNode; top?: boolean;
}) {
  return (
    <label style={{ display: "flex", alignItems: top ? "flex-start" : "center", gap: 5, cursor: "pointer", fontSize: 12 }}>
      <input
        type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)}
        style={{ width: 13, height: 13, accentColor: "#1e3a52", flexShrink: 0, marginTop: top ? 2 : 0, cursor: "pointer" }}
      />
      {children}
    </label>
  );
}

function BRow({ label, value, onChange, tL, fL, mw = 400 }: {
  label: string; value: boolean | null; onChange: (v: boolean | null) => void;
  tL: string; fL: string; mw?: number;
}) {
  return (
    <div className="pf" style={{ display: "flex", alignItems: "flex-start", gap: 8, flexWrap: "wrap", marginBottom: 5 }}>
      <span style={{ minWidth: mw, fontSize: 12, color: "#333", lineHeight: 1.4 }}>{label}</span>
      <div className="pgap" style={{ display: "flex", gap: "3px 14px", flexWrap: "wrap", paddingTop: 1 }}>
        <CB checked={value === true}  onChange={() => onChange(value === true  ? null : true)}>{tL}</CB>
        <CB checked={value === false} onChange={() => onChange(value === false ? null : false)}>{fL}</CB>
      </div>
    </div>
  );
}

function Sub({ children }: { children: React.ReactNode }) {
  return (
    <div className="psub" style={{ marginLeft: 14, marginTop: 5, paddingLeft: 10, borderLeft: "2px solid #e5e7eb" }}>
      {children}
    </div>
  );
}

function CBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="pcb pf" style={{
      border: "1px solid #ced4da", borderRadius: 4,
      padding: "8px 11px", marginBottom: 7, background: "#fafbfc",
    }}>
      {children}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Page
// ─────────────────────────────────────────────────────────────────────────────
export default function ReviewFormPage() {
  const params    = useParams();
  const sessionId = params.session_id as string;

  const [summary, setSummary] = useState<ReviewSummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [form,    setForm]    = useState<FormState | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    (async () => {
      try {
        const data = await getReviewSummary(sessionId);
        setSummary(data);
        setForm(buildFormState(data));
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    })();
  }, [sessionId]);

  useEffect(() => {
    const el = document.createElement("style");
    el.innerHTML = PRINT_CSS;
    document.head.appendChild(el);
    return () => { document.head.removeChild(el); };
  }, []);

  if (loading) return <div style={{ padding: 24, ...font }}>กำลังโหลด...</div>;
  if (!summary || !form) return <div style={{ padding: 24, ...font }}>ไม่พบข้อมูล</div>;

  const set = <K extends keyof FormState>(k: K, v: FormState[K]) =>
    setForm(p => p ? { ...p, [k]: v } : p);

  const setC4 = (i: number, v: boolean | null) =>
    setForm(p => { if (!p) return p; const c4 = [...p.c4]; c4[i] = v; return { ...p, c4 }; });

  const setC6 = (i: number, v: boolean | null) =>
    setForm(p => { if (!p) return p; const c6 = [...p.c6]; c6[i] = v; return { ...p, c6 }; });

  const c4Labels = [
    "๓.๑) ชื่อหรือตำแหน่งของเจ้าหน้าที่หน่วยรับตรวจผู้ถูกร้องเรียน",
    "๓.๒) ชื่อหน่วยรับตรวจ หรือบุคคลที่เกี่ยวข้อง",
    "๓.๓) วัน เวลา หรือช่วงเวลา สถานที่ที่มีการกระทำผิด",
    "๓.๔) และพฤติการณ์แห่งการกระทำผิด",
  ];

  return (
    // Outer: fills parent column (Next.js layout already provides sidebar + topbar)
    <div style={{ display: "flex", flexDirection: "column", height: "100%", ...font }}>

      {/* Toolbar — hidden on print because body { visibility:hidden } */}
      <div className="no-print" style={{
        flexShrink: 0, display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "7px 18px", background: "#1e3a52", borderBottom: "1px solid #16304a",
      }}>
        <span style={{ color: "#fff", fontSize: 13.5, fontWeight: 600 }}>
          แบบพิจารณารับ/ไม่รับเรื่องร้องเรียน
        </span>
        <button
          onClick={() => window.print()}
          style={{
            ...font, background: "#d97706", color: "#fff", border: "none",
            padding: "5px 14px", borderRadius: 4, fontSize: 12.5, fontWeight: 600, cursor: "pointer",
          }}
        >
          🖨️ พิมพ์ / PDF
        </button>
      </div>

      {/* Scrollable wrapper */}
      <div id="scroll-wrapper" style={{ flex: 1, overflowY: "auto", background: "#eff1f4", padding: "16px 0 32px" }}>

        {/*
          #print-area is the ONLY element made visible during printing.
          position:fixed pulls it out of the scroll container so the
          browser can render all pages without clipping.
        */}
        <div
          id="print-area"
          style={{
            width: 760, margin: "0 auto", background: "#fff",
            boxShadow: "0 1px 6px rgba(0,0,0,.1)", padding: "24px 32px",
            boxSizing: "border-box", fontSize: 12, color: "#1a1a2e", lineHeight: 1.5,
          }}
        >
          {/* Title */}
          <div style={{ textAlign: "center", fontWeight: 700, fontSize: 13.5, color: "#1e3a52", marginBottom: 2 }}>
            แบบพิจารณารับ/ไม่รับเรื่องร้องเรียน
          </div>
          <div style={{ textAlign: "center", fontSize: 11, color: "#666", marginBottom: 12 }}>
            (ทางเว็บไซต์หรือไปรษณีย์อิเล็กทรอนิกส์ของสำนักงาน)
          </div>
          <Div />

          {/* OCR */}
          <div className="pf" style={{ marginBottom: 9 }}>
            <FL>ข้อเท็จจริงจากเรื่องร้องเรียน (ประเด็นร้องเรียน)</FL>
            <textarea rows={3} value={form.ocr_text}
              onChange={e => set("ocr_text", e.target.value)}
              placeholder="กรอกข้อเท็จจริงและประเด็นร้องเรียน..." style={inputSt} />
          </div>

          {/* c1 */}
          <div className="pf" style={{ marginBottom: 9 }}>
            <FL>เรื่องร้องเรียนอยู่ในหน้าที่และเขตอำนาจการตรวจสอบของสำนัก</FL>
            <div className="pgap" style={{ display: "flex", gap: "3px 18px", marginTop: 3 }}>
              <CB checked={form.c1 === true}  onChange={() => set("c1", form.c1 === true  ? null : true)}>อยู่</CB>
              <CB checked={form.c1 === false} onChange={() => set("c1", form.c1 === false ? null : false)}>ไม่อยู่ (ข้ามไปข้อ ๘)</CB>
            </div>
          </div>

          <Div />
          <SHdr>หลักเกณฑ์และเงื่อนไขการพิจารณารับเรื่องไว้ตรวจสอบตามอำนาจหน้าที่ (ระเบียบ ข้อ ๑๘, ๑๙, ๒๐ และ ๒๑)</SHdr>

          {/* ข้อ 18 */}
          <SHdr sub>หลักเกณฑ์ตามข้อ ๑๘</SHdr>

          <BRow
            label="๑) เป็นเรื่องที่อยู่ในหน้าที่และอำนาจในการตรวจสอบของ ผตง. ตาม พ.ร.ป. ว่าด้วยการตรวจเงินแผ่นดิน พ.ศ. ๒๕๖๑ เนื่องจากเป็นเรื่องเกี่ยวกับการใช้จ่ายเงินงบประมาณ"
            value={form.c2} onChange={v => set("c2", v)} tL="อยู่" fL="ไม่อยู่"
          />
          <Div thin />

          {/* c3 */}
          <div className="pf" style={{ display: "flex", alignItems: "flex-start", gap: 8, flexWrap: "wrap", marginBottom: 5 }}>
            <span style={{ minWidth: 400, fontSize: 12, color: "#333", lineHeight: 1.4 }}>
              ๒) เป็นเรื่องที่เกิดขึ้นมาแล้วไม่เกิน ๕ ปี นับแต่วันที่เกิดเหตุจนถึงวันที่ สตง. ได้รับเรื่อง
            </span>
            <div className="pgap" style={{ display: "flex", gap: "3px 14px", flexWrap: "wrap", paddingTop: 1 }}>
              <CB checked={form.c3 === true}  onChange={() => set("c3", form.c3 === true  ? null : true)}>ไม่เกิน</CB>
              <CB checked={form.c3 === false} onChange={() => set("c3", form.c3 === false ? null : false)}>เกิน</CB>
              <CB checked={form.c3 === null}  onChange={() => set("c3", null)}>ไม่ระบุ</CB>
            </div>
          </div>
          <Div thin />

          {/* c4 */}
          <div className="pf" style={{ marginBottom: 5 }}>
            <FL>๓) ระบุรายละเอียดเพียงพอที่จะตรวจสอบได้ดังนี้</FL>
            <Sub>
              {c4Labels.map((lbl, i) => (
                <BRow key={i} label={lbl} value={form.c4[i] ?? null}
                  onChange={v => setC4(i, v)} tL="เพียงพอ" fL="ไม่ชัดเจน/ไม่ระบุ" mw={310} />
              ))}
            </Sub>
          </div>
          <Div thin />

          <BRow
            label="๔) เป็นเรื่องที่ ผตง. หรือผู้ที่ ผตง. มอบหมาย แจ้งผลการตรวจสอบ"
            value={form.c5} onChange={v => set("c5", v)} tL="ไม่เคยแจ้ง" fL="เคยแจ้ง"
          />

          <Div />

          {/* ข้อ 19 */}
          <SHdr sub>เงื่อนไขตามข้อ ๑๙ รายละเอียดเกี่ยวกับผู้ร้องเรียน</SHdr>

          <div className="pf" style={{ display: "flex", alignItems: "flex-start", gap: 8, flexWrap: "wrap", marginBottom: 5 }}>
            <span style={{ minWidth: 160, fontSize: 12, color: "#333" }}>๑) ชื่อ - สกุล</span>
            <div className="pgap" style={{ display: "flex", gap: "3px 14px" }}>
              <CB checked={form.c6[0] === true}  onChange={() => setC6(0, form.c6[0] === true  ? null : true)}>ครบถ้วน</CB>
              <CB checked={form.c6[0] === false} onChange={() => setC6(0, form.c6[0] === false ? null : false)}>ไม่ครบถ้วน/ไม่ระบุ</CB>
              <CB checked={form.c6[0] === null}  onChange={() => setC6(0, null)}>ใช้ชื่อปลอม</CB>
            </div>
          </div>
          <BRow label="๒) เลขประจำตัวประชาชน" value={form.c6[1] ?? null} onChange={v => setC6(1, v)} tL="มี" fL="ไม่มี/ไม่สมบูรณ์" mw={160} />
          <BRow label="๓) ที่อยู่หรือข้อมูลอื่นใดของผู้ร้องเรียนที่สามารถติดต่อได้" value={form.c6[2] ?? null} onChange={v => setC6(2, v)} tL="เพียงพอ" fL="ไม่ชัดเจน/ไม่ระบุ" mw={160} />

          <Div />

          {/* ข้อ 20 */}
          <SHdr sub>เงื่อนไขตามข้อ ๒๐</SHdr>
          <p style={{ fontSize: 11.5, color: "#555", margin: "3px 0 5px", lineHeight: 1.4 }}>
            เป็นเรื่องร้องเรียนที่อยู่ระหว่างการดำเนินการของหน่วยงานอื่นและเป็นเรื่องที่มีข้อเท็จจริงหรือมีประเด็นเดียวกันกับเรื่องที่ร้องเรียน
          </p>
          <div className="pgap" style={{ display: "flex", gap: "3px 18px", marginBottom: 5 }}>
            <CB checked={form.c7_no}  onChange={v => set("c7_no",  v)}>ไม่ปรากฏข้อเท็จจริง</CB>
            <CB checked={form.c7_yes} onChange={v => set("c7_yes", v)}>ปรากฏข้อเท็จจริงว่า</CB>
          </div>
          <input type="text" value={form.c7_reason} onChange={e => set("c7_reason", e.target.value)}
            placeholder="ระบุหน่วยงานที่เกี่ยวข้อง..." style={inputSt} />

          <Div />

          {/* ข้อ 21 */}
          <SHdr sub>หลักเกณฑ์และเงื่อนไขตามข้อ ๒๑ การให้ความร่วมมือระหว่างองค์กรอิสระอื่น</SHdr>

          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            <CB checked={form.c8_true} onChange={v => set("c8_true", v)} top>
              ประเด็นร้องเรียนไม่อยู่ในหน้าที่และอำนาจตรวจสอบของ ผตง. แต่อยู่ในหน้าที่และอำนาจดำเนินการขององค์กรอิสระอื่น (ระบุ)
            </CB>
            <input type="text" value={form.c8_true_reason} onChange={e => set("c8_true_reason", e.target.value)}
              placeholder="ระบุองค์กรอิสระ..." style={{ ...inputSt, marginLeft: 18 }} />

            <CB checked={form.c8_false} onChange={v => set("c8_false", v)} top>
              ประเด็นร้องเรียนบางประเด็นอยู่ในหน้าที่และอำนาจตรวจสอบของ ผตง. และมีบางประเด็นอยู่ในหน้าที่และอำนาจดำเนินการขององค์กรอิสระอื่น (ระบุ)
            </CB>
            <input type="text" value={form.c8_false_reason} onChange={e => set("c8_false_reason", e.target.value)}
              placeholder="ระบุองค์กรอิสระ..." style={{ ...inputSt, marginLeft: 18 }} />

            <CB checked={false} onChange={() => {}} top>
              ประเด็นร้องเรียนอยู่ในหน้าที่และอำนาจตรวจสอบของ ผตง. และอาจเข้าลักษณะเป็นการกระทำความผิดที่อยู่ในหน้าที่และอำนาจตรวจสอบองค์กรอิสระอื่น
            </CB>
          </div>
          <Sub>
            {[
              "ตามกฎหมายว่าด้วยความผิดเกี่ยวกับการเสนอราคาต่อหน่วยงานของรัฐ",
              "ตามกฎหมายคณะกรรมการการเลือกตั้ง",
              "ตามกฎหมายผู้ตรวจการแผ่นดิน",
              "ตามกฎหมายคณะกรรมการสิทธิมนุษยชนแห่งชาติ",
            ].map(lbl => <CB key={lbl} checked={false} onChange={() => {}}>{lbl}</CB>)}
          </Sub>

          {/* Page break: conclusion on page 2 */}
          <div className="page-break" style={{ display: "none" }} />

          <Div />
          <SHdr>สรุปความเห็นของผู้พิจารณา</SHdr>

          {/* 1. รับเรื่อง */}
          <CBox>
            <CB checked={form.conclusion_accept} onChange={v => set("conclusion_accept", v)} top>
              <span style={{ fontWeight: 700, fontSize: 12 }}>รับเรื่องไว้ตรวจสอบ</span>
            </CB>
            <Sub>
              <FL>ประเด็นที่</FL>
              <input type="text" value={form.conclusion_accept_topic}
                onChange={e => set("conclusion_accept_topic", e.target.value)}
                placeholder="ระบุประเด็นที่รับ..." style={inputSt} />
              <p style={{ fontSize: 10.5, color: "#666", marginTop: 3, lineHeight: 1.4 }}>
                ตามหลักเกณฑ์และเงื่อนไขของระเบียบ สตง. ว่าด้วยการตรวจสอบการปฏิบัติตามกฎหมาย พ.ศ. ๒๕๖๖ ข้อ ๑๘ และ ๒๐
              </p>
            </Sub>
          </CBox>

          {/* 2. ไม่รับเรื่อง */}
          <CBox>
            <CB checked={form.conclusion_reject} onChange={v => set("conclusion_reject", v)} top>
              <span style={{ fontWeight: 700, fontSize: 12 }}>ไม่รับเรื่องไว้ตรวจสอบ</span>
            </CB>
            <Sub>
              <FL>ประเด็นที่</FL>
              <input type="text" value={form.conclusion_reject_topic}
                onChange={e => set("conclusion_reject_topic", e.target.value)}
                placeholder="ระบุประเด็นที่ไม่รับ..." style={{ ...inputSt, marginBottom: 4 }} />
              <FL>เนื่องจาก</FL>
              <textarea rows={2} value={form.conclusion_reject_reason}
                onChange={e => set("conclusion_reject_reason", e.target.value)}
                placeholder="ระบุเหตุผล..." style={{ ...inputSt, marginBottom: 4 }} />
              <CB checked={form.conclusion_reject_notify} onChange={v => set("conclusion_reject_notify", v)}>
                แจ้งผู้ร้องเรียนทราบ (ตามเงื่อนไขข้อ ๒๒ วรรคสอง)
              </CB>
            </Sub>
          </CBox>

          {/* 3. ไม่รับ แต่เข้าข้อ 21 */}
          <CBox>
            <CB checked={form.conclusion_art21} onChange={v => set("conclusion_art21", v)} top>
              <span style={{ fontWeight: 700, fontSize: 12 }}>ไม่รับเรื่องไว้ตรวจสอบ แต่เข้าหลักเกณฑ์และเงื่อนไขตามข้อ ๒๑</span>
            </CB>
            <Sub>
              <FL>ประเด็นที่ (ตามข้อ ๒๑(๑) หรือ (๒))</FL>
              <input type="text" value={form.conclusion_art21_topic_12}
                onChange={e => set("conclusion_art21_topic_12", e.target.value)}
                placeholder="ระบุประเด็น..." style={inputSt} />
              <p style={{ fontSize: 10.5, color: "#666", margin: "2px 0 4px", lineHeight: 1.4 }}>
                เนื่องจาก: ประเด็นร้องเรียนไม่อยู่ในหน้าที่และอำนาจตรวจสอบของ ผตง. แต่อยู่ในหน้าที่และอำนาจดำเนินการขององค์กรอิสระอื่น ตามข้อ ๒๑ (๑) หรือ (๒)
              </p>
              <FL>ประเด็นที่ (ตามข้อ ๒๑(๓))</FL>
              <input type="text" value={form.conclusion_art21_topic_3}
                onChange={e => set("conclusion_art21_topic_3", e.target.value)}
                placeholder="ระบุประเด็น..." style={inputSt} />
              <p style={{ fontSize: 10.5, color: "#666", margin: "2px 0 4px", lineHeight: 1.4 }}>
                เนื่องจาก: ประเด็นร้องเรียนอยู่ในหน้าที่และอำนาจตรวจสอบของ ผตง. และอาจเข้าลักษณะเป็นการกระทำความผิดที่อยู่ในหน้าที่และอำนาจตรวจสอบองค์กรอิสระอื่น ซึ่งต้องรวบรวมข้อเท็จจริงเบื้องต้นก่อน ตามข้อ ๒๑ (๓)
              </p>
              <CB checked={form.conclusion_art21_notify} onChange={v => set("conclusion_art21_notify", v)}>
                แจ้งผู้ร้องเรียนทราบ (ตามเงื่อนไขข้อ ๒๒ วรรคสอง)
              </CB>
            </Sub>
          </CBox>

          {/* 4. อื่น ๆ */}
          <CBox>
            <CB checked={form.conclusion_other} onChange={v => set("conclusion_other", v)} top>
              <span style={{ fontWeight: 700, fontSize: 12 }}>อื่น ๆ</span>
            </CB>
            <Sub>
              <textarea rows={2} value={form.conclusion_other_text}
                onChange={e => set("conclusion_other_text", e.target.value)}
                placeholder="ระบุข้อมูลเพิ่มเติม..." style={{ ...inputSt, marginTop: 4 }} />
            </Sub>
          </CBox>

        </div>{/* /print-area */}
      </div>{/* /scrollable */}
    </div>
  );
}
