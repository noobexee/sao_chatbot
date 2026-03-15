from langchain_core.prompts import ChatPromptTemplate

KEYWORD_SYSTEM_PROMPT = """
You are a Thai Legal Search Expert. Your task is to extract search keywords 
from a user's query to be used in a BM25 keyword search engine.

Rules:
1. Prioritize Entities: Always extract Government Ministries (กระทรวง) and Departments (กรม).
2. Identify Actions: Extract core legal actions or subjects (e.g., เรื่องร้องเรียน, การใช้จ่ายเงิน).
3. No Explanations: Return ONLY a comma-separated list of Thai keywords.
4. Preserve Format: Keep Thai terminology exactly as written in the query.

Examples:
Query: "เรื่องร้องเรียนเกี่ยวกับการใช้จ่ายเงินของกรมการปกครอง กระทรวงมหาดไทย"
Keywords: กระทรวงมหาดไทย, กรมการปกครอง, เรื่องร้องเรียน, การใช้จ่ายเงิน

Query: "หลักเกณฑ์พัสดุของสำนักงานปลัดสำนักนายกรัฐมนตรี"
Keywords: สำนักงานปลัดสำนักนายกรัฐมนตรี, หลักเกณฑ์พัสดุ
"""

def build_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", KEYWORD_SYSTEM_PROMPT),
        ("human", """
        USER QUERY: "{query}"
        KEYWORDS:
        """),
    ])