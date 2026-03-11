"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getReviewSummary, ReviewSummaryData } from "../../../libs/initialReview/getSummaray";

// ─────────────────────────────────────────────────────────────────────────────
// Print CSS
// ─────────────────────────────────────────────────────────────────────────────
const PRINT_CSS = `
@media print {
  @page { size: A4 portrait; margin: 15mm 18mm; }

  .no-print { display: none !important; }

  body          { visibility: hidden !important; }
  #print-area   { visibility: visible !important; }
  #print-area * { visibility: visible !important; }

  html, body, #__next, #scroll-wrapper, body > div, body > div > div {
    overflow: visible !important;
    height: auto !important;
    max-height: none !important;
  }

  #print-area {
    position: static !important;
    display: block !important;
    width: 100% !important;
    height: auto !important;
    overflow: visible !important;
    padding: 0 !important;
    margin: 0 !important;
    box-shadow: none !important;
    background: white !important;
    font-size: 9pt !important;
    box-sizing: border-box !important;
    color: #000 !important;
  }

  /* underline inputs: hide placeholder, show only text + underline */
  #print-area input[type=text],
  #print-area textarea {
    border: none !important;
    border-bottom: 0.5pt solid #000 !important;
    background: transparent !important;
    font-size: 9pt !important;
    padding: 0 2pt !important;
    outline: none !important;
    box-shadow: none !important;
    resize: none !important;
    -webkit-print-color-adjust: exact;
  }

  #print-area .page-break { page-break-before: always !important; display: block !important; }
  #print-area .no-break { page-break-inside: avoid !important; }
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
  c8_other: boolean;
  c8_laws: boolean[];
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
    c7_reason: c7_yes ? ((s.criteria_7 as Record<string,string>)["false"] ?? "") : "",
    c8_true, c8_false, c8_other: false, c8_laws: [false, false, false, false],
    c8_true_reason:  c8_true  ? ((s.criteria_8 as Record<string,string>)["true"]  ?? "") : "",
    c8_false_reason: c8_false ? ((s.criteria_8 as Record<string,string>)["false"] ?? "") : "",
    conclusion_accept: false, conclusion_accept_topic: "",
    conclusion_reject: false, conclusion_reject_topic: "",
    conclusion_reject_reason: "", conclusion_reject_notify: false,
    conclusion_art21: false, conclusion_art21_topic_12: "",
    conclusion_art21_topic_3: "", conclusion_art21_notify: false,
    conclusion_other: false, conclusion_other_text: "",
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Design tokens — formal government document style
// ─────────────────────────────────────────────────────────────────────────────
const FONT = "'Sarabun', 'TH Sarabun New', sans-serif";
const FS   = 13.5; // base font size px (screen); prints as 9pt

const base: React.CSSProperties = { fontFamily: FONT, fontSize: FS, color: "#000", lineHeight: 1.65 };

// Underline input — screen shows light border box, print shows only bottom line
const uSt = (w: string | number = "100%", inline = false): React.CSSProperties => ({
  fontFamily: FONT, fontSize: FS, color: "#000",
  border: "1px solid #bbb", borderRadius: 2,
  background: "#fdfdfb", outline: "none",
  padding: "2px 6px", width: w, boxSizing: "border-box" as const,
  display: inline ? "inline" : "block",
  resize: "vertical" as const,
});

// ─────────────────────────────────────────────────────────────────────────────
// Atoms
// ─────────────────────────────────────────────────────────────────────────────

/** Checkbox rendered as ☐ / ☑ — no native checkbox shown */
function Ck({ v, on, children, top }: {
  v: boolean; on: (x: boolean) => void;
  children?: React.ReactNode; top?: boolean;
}) {
  return (
    <label style={{ display: "inline-flex", alignItems: top ? "flex-start" : "center",
      gap: 4, cursor: "pointer", fontFamily: FONT, fontSize: FS, userSelect: "none" }}>
      <span onClick={() => on(!v)}
        style={{ fontSize: 17, lineHeight: 1, flexShrink: 0, marginTop: top ? 2 : 0 }}>
        {v ? "☑" : "☐"}
      </span>
      {children && <span>{children}</span>}
    </label>
  );
}

/** Horizontal rule */
function Rule({ heavy }: { heavy?: boolean }) {
  return <hr style={{ border: "none",
    borderTop: heavy ? "1.5px solid #000" : "0.5px solid #999",
    margin: heavy ? "10px 0 8px" : "5px 0" }} />;
}

/** Bold section title with left border — matches template */
function STitle({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ ...base, fontWeight: 700, fontSize: 13.5,
      borderLeft: "3px solid #000", paddingLeft: 8,
      marginTop: 6, marginBottom: 5 }}>
      {children}
    </div>
  );
}

/** Sub-section label, slightly smaller */
function Sub({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ ...base, fontWeight: 700, fontSize: 13, marginTop: 8, marginBottom: 4 }}>
      {children}
    </div>
  );
}

/** A row: label left, checkboxes right — matches template column layout */
function Row({ label, checks, indent = 0 }: {
  label: React.ReactNode;
  checks: React.ReactNode;
  indent?: number;
}) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 10,
      marginBottom: 4, paddingLeft: indent }}>
      <div style={{ ...base, flex: "1 1 0", minWidth: 0 }}>{label}</div>
      <div style={{ display: "flex", gap: 18, flexShrink: 0, paddingTop: 1, flexWrap: "wrap" }}>
        {checks}
      </div>
    </div>
  );
}

/** Inline text input — underlined, no box */
function TIn({ v, on, w = "100%", ph = "" }: {
  v: string; on: (x: string) => void; w?: string | number; ph?: string;
}) {
  return (
    <input type="text" value={v} onChange={e => on(e.target.value)}
      placeholder={ph} style={uSt(w)} />
  );
}

/** Multi-line underlined block */
function TBox({ v, on, rows = 3, ph = "" }: {
  v: string; on: (x: string) => void; rows?: number; ph?: string;
}) {
  return (
    <textarea value={v} onChange={e => on(e.target.value)}
      rows={rows} placeholder={ph} style={{ ...uSt("100%"), resize: "vertical" }} />
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

  if (loading) return <div style={{ padding: 24, fontFamily: FONT }}>กำลังโหลด...</div>;
  if (!summary || !form) return <div style={{ padding: 24, fontFamily: FONT }}>ไม่พบข้อมูล</div>;

  const set  = <K extends keyof FormState>(k: K, v: FormState[K]) =>
    setForm(p => p ? { ...p, [k]: v } : p);
  const setC4 = (i: number, v: boolean | null) =>
    setForm(p => { if (!p) return p; const c4=[...p.c4]; c4[i]=v; return {...p,c4}; });
  const setC6 = (i: number, v: boolean | null) =>
    setForm(p => { if (!p) return p; const c6=[...p.c6]; c6[i]=v; return {...p,c6}; });
  const setC8Law = (i: number, v: boolean) =>
    setForm(p => { if (!p) return p; const c8_laws=[...p.c8_laws]; c8_laws[i]=v; return {...p,c8_laws}; });
  // toggle: clicking checked option deselects it
  const tog = (cur: boolean | null, target: boolean): boolean | null =>
    cur === target ? null : target;

  // ── Paper styles ──
  const paper: React.CSSProperties = {
    width: 794, margin: "0 auto", background: "#fff",
    boxShadow: "0 2px 16px rgba(0,0,0,.12)",
    padding: "40px 52px", boxSizing: "border-box",
    ...base,
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", fontFamily: FONT }}>

      {/* ── Toolbar ── */}
      <div className="no-print" style={{
        flexShrink: 0, display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "7px 20px", background: "#1e3a52",
      }}>
        <span style={{ color: "#fff", fontSize: 14, fontWeight: 600, fontFamily: FONT }}>
          แบบพิจารณารับ/ไม่รับเรื่องร้องเรียน
        </span>
        <button onClick={() => window.print()} style={{
          fontFamily: FONT, background: "#c05621", color: "#fff", border: "none",
          padding: "5px 16px", borderRadius: 3, fontSize: 13, fontWeight: 600, cursor: "pointer",
        }}>
          🖨 พิมพ์ / PDF
        </button>
      </div>

      {/* ── Scroll wrapper ── */}
      <div id="scroll-wrapper" style={{ flex: 1, overflowY: "auto", background: "#dde1e7", padding: "24px 0 48px" }}>

        <div id="print-area" style={paper}>

          {/* ════════════════════════════════════════
              HEADER
          ════════════════════════════════════════ */}
          <div style={{ textAlign: "center", fontWeight: 700, fontSize: 16, marginBottom: 2 }}>
            แบบพิจารณารับ/ไม่รับเรื่องร้องเรียน
          </div>
          <div style={{ textAlign: "center", fontSize: 12.5, color: "#555", marginBottom: 14 }}>
            (ทางเว็บไซต์หรือไปรษณีย์อิเล็กทรอนิกส์ของสำนักงาน)
          </div>
          <Rule heavy />

          {/* ════════════════════════════════════════
              ข้อเท็จจริงจากเรื่องร้องเรียน
          ════════════════════════════════════════ */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ ...base, fontWeight: 600, marginBottom: 4 }}>
              ข้อเท็จจริงจากเรื่องร้องเรียน (ประเด็นร้องเรียน)
            </div>
            <TBox v={form.ocr_text} on={v => set("ocr_text", v)} rows={3}
              ph="กรอกข้อเท็จจริงและประเด็นร้องเรียน..." />
          </div>

          {/* ════════════════════════════════════════
              c1 — อยู่ในหน้าที่
          ════════════════════════════════════════ */}
          <Row
            label={<span style={{ fontWeight: 600 }}>เรื่องร้องเรียนอยู่ในหน้าที่และเขตอำนาจการตรวจสอบของสำนัก</span>}
            checks={<>
              <Ck v={form.c1===true}  on={() => set("c1", tog(form.c1,true))}>อยู่</Ck>
              <Ck v={form.c1===false} on={() => set("c1", tog(form.c1,false))}>ไม่อยู่ (ข้ามไปข้อ ๘)</Ck>
            </>}
          />

          <Rule heavy />
          <STitle>หลักเกณฑ์และเงื่อนไขการพิจารณารับเรื่องไว้ตรวจสอบตามอำนาจหน้าที่ (ตามระเบียบ ข้อ ๑๘, ๑๙, ๒๐ และ ๒๑)</STitle>

          {/* ════════════════════════════════════════
              ข้อ ๑๘
          ════════════════════════════════════════ */}
          <Sub>หลักเกณฑ์ตามข้อ ๑๘</Sub>

          {/* c2 */}
          <Row
            label="๑) เป็นเรื่องที่อยู่ในหน้าที่และอำนาจในการตรวจสอบของ ผตง. ตาม พ.ร.ป. ว่าด้วยการตรวจเงินแผ่นดิน พ.ศ. ๒๕๖๑ เนื่องจากเป็นเรื่องเกี่ยวกับการใช้จ่ายเงินงบประมาณ"
            checks={<>
              <Ck v={form.c2===true}  on={() => set("c2", tog(form.c2,true))}>อยู่</Ck>
              <Ck v={form.c2===false} on={() => set("c2", tog(form.c2,false))}>ไม่อยู่</Ck>
            </>}
          />
          <Rule />

          {/* c3 */}
          <Row
            label="๒) เป็นเรื่องที่เกิดขึ้นมาแล้วไม่เกิน ๕ ปี นับแต่วันที่เกิดเหตุจนถึงวันที่ สตง. ได้รับเรื่อง"
            checks={<>
              <Ck v={form.c3===true}  on={() => set("c3", tog(form.c3,true))}>ไม่เกิน</Ck>
              <Ck v={form.c3===false} on={() => set("c3", tog(form.c3,false))}>เกิน</Ck>
              <Ck v={form.c3===null && form.c3!==undefined} on={() => set("c3",null)}>ไม่ระบุ</Ck>
            </>}
          />
          <Rule />

          {/* c4 */}
          <div style={{ ...base, marginBottom: 2 }}>๓) ระบุรายละเอียดเพียงพอที่จะตรวจสอบได้ดังนี้</div>
          {[
            "๓.๑) ชื่อหรือตำแหน่งของเจ้าหน้าที่หน่วยรับตรวจผู้ถูกร้องเรียน",
            "๓.๒) ชื่อหน่วยรับตรวจ หรือบุคคลที่เกี่ยวข้อง",
            "๓.๓) วัน เวลา หรือช่วงเวลา สถานที่ที่มีการกระทำผิด",
            "๓.๔) และพฤติการณ์แห่งการกระทำผิด",
          ].map((lbl, i) => (
            <Row key={i} label={lbl} indent={16}
              checks={<>
                <Ck v={form.c4[i]===true}  on={() => setC4(i, tog(form.c4[i],true))}>เพียงพอ</Ck>
                <Ck v={form.c4[i]===false} on={() => setC4(i, tog(form.c4[i],false))}>ไม่ชัดเจน/ไม่ระบุ</Ck>
              </>}
            />
          ))}
          <Rule />

          {/* c5 */}
          <Row
            label="๔) เป็นเรื่องที่ ผตง. หรือผู้ที่ ผตง. มอบหมาย แจ้งผลการตรวจสอบ"
            checks={<>
              <Ck v={form.c5===true}  on={() => set("c5", tog(form.c5,true))}>ไม่เคยแจ้ง</Ck>
              <Ck v={form.c5===false} on={() => set("c5", tog(form.c5,false))}>เคยแจ้ง</Ck>
            </>}
          />

          <Rule heavy />

          {/* ════════════════════════════════════════
              ข้อ ๑๙
          ════════════════════════════════════════ */}
          <Sub>เงื่อนไขตามข้อ ๑๙ รายละเอียดเกี่ยวกับผู้ร้องเรียน</Sub>

          {/* c6[0] ชื่อ — 3 options on same line */}
          <Row
            label="๑) ชื่อ - สกุล"
            checks={<>
              <Ck v={form.c6[0]===true}  on={() => setC6(0, tog(form.c6[0],true))}>ครบถ้วน</Ck>
              <Ck v={form.c6[0]===false} on={() => setC6(0, tog(form.c6[0],false))}>ไม่ครบถ้วน/ไม่ระบุ</Ck>
              <Ck v={form.c6[0]===null}  on={() => setC6(0, null)}>ใช้ชื่อปลอม</Ck>
            </>}
          />
          <Row
            label="๒) เลขประจำตัวประชาชน"
            checks={<>
              <Ck v={form.c6[1]===true}  on={() => setC6(1, tog(form.c6[1],true))}>มี</Ck>
              <Ck v={form.c6[1]===false} on={() => setC6(1, tog(form.c6[1],false))}>ไม่มี/ไม่สมบูรณ์</Ck>
            </>}
          />
          <Row
            label="๓) ที่อยู่หรือข้อมูลอื่นใดของผู้ร้องเรียนที่สามารถติดต่อได้"
            checks={<>
              <Ck v={form.c6[2]===true}  on={() => setC6(2, tog(form.c6[2],true))}>เพียงพอ</Ck>
              <Ck v={form.c6[2]===false} on={() => setC6(2, tog(form.c6[2],false))}>ไม่ชัดเจน/ไม่ระบุ</Ck>
            </>}
          />

          <Rule heavy />

          {/* ════════════════════════════════════════
              ข้อ ๒๐
          ════════════════════════════════════════ */}
          <Sub>เงื่อนไขตามข้อ ๒๐</Sub>
          <div style={{ ...base, marginBottom: 6, fontSize: 13 }}>
            เป็นเรื่องร้องเรียนที่อยู่ระหว่างการดำเนินการของหน่วยงานอื่นและเป็นเรื่องที่มีข้อเท็จจริงหรือมีประเด็นเดียวกันกับเรื่องที่ร้องเรียน
          </div>

          {/* ไม่ปรากฏ — own line */}
          <div style={{ marginBottom: 4 }}>
            <Ck v={form.c7_no} on={v => set("c7_no",v)}>ไม่ปรากฏข้อเท็จจริง</Ck>
          </div>

          {/* ปรากฏ + inline underline */}
          <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:6 }}>
            <Ck v={form.c7_yes} on={v => set("c7_yes",v)}>ปรากฏข้อเท็จจริงว่า</Ck>
            <div style={{ flex:1 }}>
              <TIn v={form.c7_reason} on={v => set("c7_reason",v)} ph="ระบุหน่วยงาน..." />
            </div>
          </div>

          <Rule heavy />

          {/* ════════════════════════════════════════
              ข้อ ๒๑
          ════════════════════════════════════════ */}
          <Sub>หลักเกณฑ์และเงื่อนไขตามข้อ ๒๑ การให้ความร่วมมือระหว่างองค์กรอิสระอื่น</Sub>

          {/* c8_true */}
          <div style={{ marginBottom: 5 }}>
            <Ck v={form.c8_true} on={v => set("c8_true",v)} top>
              <span>ประเด็นร้องเรียนไม่อยู่ในหน้าที่และอำนาจตรวจสอบของ ผตง. แต่อยู่ในหน้าที่และอำนาจดำเนินการขององค์กรอิสระอื่น (ระบุ)</span>
            </Ck>
            <div style={{ paddingLeft: 24, marginTop: 3 }}>
              <TIn v={form.c8_true_reason} on={v => set("c8_true_reason",v)} ph="ระบุชื่อองค์กร..." />
            </div>
          </div>

          {/* c8_false */}
          <div style={{ marginBottom: 5 }}>
            <Ck v={form.c8_false} on={v => set("c8_false",v)} top>
              <span>ประเด็นร้องเรียนบางประเด็นอยู่ในหน้าที่และอำนาจตรวจสอบของ ผตง. และมีบางประเด็นอยู่ในหน้าที่และอำนาจดำเนินการขององค์กรอิสระอื่น (ระบุ)</span>
            </Ck>
            <div style={{ paddingLeft: 24, marginTop: 3 }}>
              <TIn v={form.c8_false_reason} on={v => set("c8_false_reason",v)} ph="ระบุชื่อองค์กร..." />
            </div>
          </div>

          {/* c8_other */}
          <div style={{ marginBottom: 4 }}>
            <Ck v={form.c8_other} on={v => set("c8_other",v)} top>
              <span>ประเด็นร้องเรียนอยู่ในหน้าที่และอำนาจตรวจสอบของ ผตง. และอาจเข้าลักษณะเป็นการกระทำความผิดที่อยู่ในหน้าที่และอำนาจตรวจสอบองค์กรอิสระอื่น</span>
            </Ck>
          </div>

          {/* sub-laws indented — tickable */}
          <div style={{ paddingLeft: 24, display:"flex", flexDirection:"column", gap:3 }}>
            {[
              "ตามกฎหมายว่าด้วยความผิดเกี่ยวกับการเสนอราคาต่อหน่วยงานของรัฐ",
              "ตามกฎหมายคณะกรรมการการเลือกตั้ง",
              "ตามกฎหมายผู้ตรวจการแผ่นดิน",
              "ตามกฎหมายคณะกรรมการสิทธิมนุษยชนแห่งชาติ",
            ].map((l, i) => (
              <Ck key={l} v={form.c8_laws[i]} on={v => setC8Law(i, v)}>{l}</Ck>
            ))}
          </div>

          {/* ════════════════════════════════════════
              PAGE 2 — สรุปความเห็น
          ════════════════════════════════════════ */}
          <div className="page-break" style={{ display:"none" }} />
          <Rule heavy />
          <STitle>สรุปความเห็นของผู้พิจารณา</STitle>

          {/* ─── 1. รับเรื่อง ─── */}
          <div className="no-break" style={{ marginBottom: 10 }}>
            {/* checkbox + "รับเรื่องไว้ตรวจสอบ" + "ประเด็นที่" + underline on same line */}
            <div style={{ display:"flex", alignItems:"baseline", gap:8, flexWrap:"wrap" }}>
              <Ck v={form.conclusion_accept} on={v => set("conclusion_accept",v)}>
                <span style={{ fontWeight:700 }}>รับเรื่องไว้ตรวจสอบ</span>
              </Ck>
              <span style={{ ...base }}>ประเด็นที่</span>
              <div style={{ flex:1, minWidth:160 }}>
                <TIn v={form.conclusion_accept_topic} on={v => set("conclusion_accept_topic",v)} ph="ระบุประเด็น" />
              </div>
            </div>
            <div style={{ ...base, fontSize:12.5, color:"#444", paddingLeft:24, marginTop:3 }}>
              ตามหลักเกณฑ์และเงื่อนไขของระเบียบ สตง. ว่าด้วยการตรวจสอบการปฏิบัติตามกฎหมาย พ.ศ. ๒๕๖๖ ข้อ ๑๘ และ ๒๐
            </div>
          </div>

          <Rule />

          {/* ─── 2. ไม่รับเรื่อง ─── */}
          <div className="no-break" style={{ marginBottom: 10 }}>
            <div style={{ display:"flex", alignItems:"baseline", gap:8, flexWrap:"wrap" }}>
              <Ck v={form.conclusion_reject} on={v => set("conclusion_reject",v)}>
                <span style={{ fontWeight:700 }}>ไม่รับเรื่องไว้ตรวจสอบ</span>
              </Ck>
              <span style={{ ...base }}>ประเด็นที่</span>
              <div style={{ flex:1, minWidth:160 }}>
                <TIn v={form.conclusion_reject_topic} on={v => set("conclusion_reject_topic",v)} ph="ระบุประเด็น" />
              </div>
            </div>
            <div style={{ display:"flex", alignItems:"baseline", gap:8, paddingLeft:24, marginTop:4, flexWrap:"wrap" }}>
              <span style={{ ...base, whiteSpace:"nowrap" }}>เนื่องจาก</span>
              <div style={{ flex:1, minWidth:200 }}>
                <TIn v={form.conclusion_reject_reason} on={v => set("conclusion_reject_reason",v)} ph="ระบุเหตุผล" />
              </div>
            </div>
            <div style={{ paddingLeft:24, marginTop:5 }}>
              <Ck v={form.conclusion_reject_notify} on={v => set("conclusion_reject_notify",v)}>
                แจ้งผู้ร้องเรียนทราบ (ตามเงื่อนไขข้อ ๒๒ วรรคสอง)
              </Ck>
            </div>
          </div>

          <Rule />

          {/* ─── 3. ไม่รับ แต่เข้าข้อ 21 ─── */}
          <div className="no-break" style={{ marginBottom: 10 }}>
            <Ck v={form.conclusion_art21} on={v => set("conclusion_art21",v)}>
              <span style={{ fontWeight:700 }}>ไม่รับเรื่องไว้ตรวจสอบ แต่เข้าหลักเกณฑ์และเงื่อนไขตามข้อ ๒๑</span>
            </Ck>

            {/* art21 (1)(2) — "ประเด็นที่ ___ เนื่องจาก ..." on same line */}
            <div style={{ display:"flex", alignItems:"baseline", gap:6, paddingLeft:24, marginTop:5, flexWrap:"wrap" }}>
              <span style={{ ...base, whiteSpace:"nowrap" }}>ประเด็นที่</span>
              <div style={{ width:100 }}>
                <TIn v={form.conclusion_art21_topic_12} on={v => set("conclusion_art21_topic_12",v)} ph="ระบุ" />
              </div>
              <span style={{ ...base, fontSize:12.5, flex:1 }}>
                เนื่องจาก ประเด็นร้องเรียนไม่อยู่ในหน้าที่และอำนาจตรวจสอบของ ผตง. แต่อยู่ในหน้าที่และอำนาจดำเนินการขององค์กรอิสระอื่น ตามข้อ ๒๑ (๑) หรือ (๒)
              </span>
            </div>

            {/* art21 (3) */}
            <div style={{ display:"flex", alignItems:"baseline", gap:6, paddingLeft:24, marginTop:5, flexWrap:"wrap" }}>
              <span style={{ ...base, whiteSpace:"nowrap" }}>ประเด็นที่</span>
              <div style={{ width:100 }}>
                <TIn v={form.conclusion_art21_topic_3} on={v => set("conclusion_art21_topic_3",v)} ph="ระบุ" />
              </div>
              <span style={{ ...base, fontSize:12.5, flex:1 }}>
                เนื่องจาก ประเด็นร้องเรียนอยู่ในหน้าที่และอำนาจตรวจสอบของ ผตง. และอาจเข้าลักษณะเป็นการกระทำความผิดที่อยู่ในหน้าที่และอำนาจตรวจสอบองค์กรอิสระอื่น ซึ่งต้องรวบรวมข้อเท็จจริงเบื้องต้นก่อน ตามข้อ ๒๑ (๓)
              </span>
            </div>

            <div style={{ paddingLeft:24, marginTop:5 }}>
              <Ck v={form.conclusion_art21_notify} on={v => set("conclusion_art21_notify",v)}>
                แจ้งผู้ร้องเรียนทราบ (ตามเงื่อนไขข้อ ๒๒ วรรคสอง)
              </Ck>
            </div>
          </div>

          <Rule />

          {/* ─── 4. อื่น ๆ ─── */}
          <div className="no-break" style={{ marginBottom: 8 }}>
            <div style={{ display:"flex", alignItems:"baseline", gap:8 }}>
              <Ck v={form.conclusion_other} on={v => set("conclusion_other",v)}>
                <span style={{ fontWeight:700 }}>อื่น ๆ</span>
              </Ck>
              <div style={{ flex:1 }}>
                <TIn v={form.conclusion_other_text} on={v => set("conclusion_other_text",v)} ph="ระบุ..." />
              </div>
            </div>
          </div>

        </div>{/* /print-area */}
      </div>{/* /scroll-wrapper */}
    </div>
  );
}
