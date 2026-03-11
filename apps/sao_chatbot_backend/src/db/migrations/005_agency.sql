CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS initial_review_agencies (
    id SERIAL PRIMARY KEY,
    agency_code VARCHAR(50),      -- รหัสหน่วยรับตรวจ
    agency_name VARCHAR(255) NOT NULL, -- ชื่อหน่วยรับตรวจ
    department_code VARCHAR(50),  -- รหัสสังกัด
    department_name VARCHAR(255), -- ชื่อสังกัด
    ministry_code VARCHAR(50),    -- รหัสกระทรวง
    ministry_name VARCHAR(255),   -- ชื่อกระทรวง
    search_key VARCHAR(255)       -- ชื่อหน่วยงานที่ Clean แล้ว (ใช้สำหรับค้นหา)
);

CREATE INDEX IF NOT EXISTS idx_agency_search_key_trgm 
ON initial_review_agencies USING GIN (search_key gin_trgm_ops);