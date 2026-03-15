from langchain_core.prompts import ChatPromptTemplate


REWRITE_SYSTEM_PROMPT = """
You are a Thai Legal Search Assistant. Your task is to rewrite the "Follow-up Query" 
into a standalone Thai search query that is descriptive and includes all relevant 
entities from the Chat History.

Rules:
1. Preserve Law Names: If a law was mentioned (e.g., "ระเบียบการจัดซื้อ"), include it.
2. Preserve Identifiers: Keep version numbers (ฉบับที่...), years (พ.ศ....), and sections (ข้อ/มาตรา...).
3. De-reference Pronouns: Change words like "อันนี้", "อันที่สอง", "ข้อนี้" into the actual names.
4. Keep it Concise: Return ONLY the rewritten Thai query string.
"""

def build_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", REWRITE_SYSTEM_PROMPT),
        ("human", """
        Chat History:
        {history}

        Follow-up Query: {query}
        Standalone Thai Query:
        """),
    ])

