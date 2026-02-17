-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ❌ REMOVED: Table 'InitialReview_sessions' 
-- เนื่องจากระบบเปลี่ยนเป็น Stateless ไม่มีการเก็บไฟล์ลง DB แล้ว

-- ✅ UPDATED: InitialReview Feedback Logs Table
-- ตารางนี้เอาไว้เก็บ Log เพื่อนำไป Train AI ต่อในอนาคต
CREATE TABLE IF NOT EXISTS InitialReview_feedback_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- InitialReview_id: เป็น Trace ID ที่ Generate ขึ้นมาใหม่ใน Memory (backend) 
    -- ใช้เพื่อ group logs ที่เกิดจากการวิเคราะห์ครั้งเดียวกัน (ไม่เป็น Foreign Key แล้ว)
    InitialReview_id UUID NOT NULL, 
    
    -- criteria_id: หมายเลขข้อ Criteria (เช่น 2, 4, 6, 8)
    criteria_id INTEGER NOT NULL,
    
    -- field_type: ประเภทข้อมูล (เช่น 'c2_result', 'people_list', 'entity', 'behavior')
    field_type VARCHAR(100) NOT NULL,
    
    -- ai_value: ค่าที่ AI ตอบกลับมา (เก็บเป็น Text หรือ JSON String)
    ai_value TEXT,
    
    -- user_edit: User มีการแก้ไขข้อมูลหรือไม่ (TRUE = แก้ไข/ไม่เห็นด้วย, FALSE = เห็นด้วย)
    user_edit BOOLEAN DEFAULT FALSE,
    
    -- user_value: ค่าใหม่ที่ User กรอก (ถ้ามีการแก้ไข)
    user_value TEXT,
    
    -- result_correct: AI ตอบถูกหรือไม่ (TRUE = ถูก, FALSE = ผิด)
    -- ใช้สำหรับวัดผล Accuracy/Recall ในภายหลัง
    result_correct BOOLEAN DEFAULT TRUE,

    -- timestamp: เวลาที่บันทึก
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for analytics performance
-- Index ที่ ID เพื่อให้ดึงข้อมูลการวิเคราะห์แต่ละรอบได้ไว
CREATE INDEX IF NOT EXISTS idx_logs_review_id ON InitialReview_feedback_logs(InitialReview_id);
-- Index ที่ Criteria เพื่อวัดผลรายข้อได้ง่าย
CREATE INDEX IF NOT EXISTS idx_logs_criteria ON InitialReview_feedback_logs(criteria_id);
-- Index ที่ Field Type เพื่อดูว่า field ไหนผิดบ่อย
CREATE INDEX IF NOT EXISTS idx_logs_field_type ON InitialReview_feedback_logs(field_type);