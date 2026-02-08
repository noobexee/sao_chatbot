import asyncio
import pandas as pd
from test.merge import get_processed_data
from src.app.chatbot.retriever import Retriever

class RAGEvaluator:
    def __init__(self):
        # Create a translator for Thai -> Arabic numerals
        self.thai_map = str.maketrans('๐๑๒๓๔๕๖๗๘๙', '0123456789')

    # --- TEXT NORMALIZATION ---
    def normalize_numerals(self, text):
        if not isinstance(text, str): return ""
        return text.translate(self.thai_map).strip()

    def normalize_text(self, text):
        if not isinstance(text, str): return ""
        # 1. Convert Numerals (๑ -> 1)
        text = self.normalize_numerals(text)
        # 2. Remove ALL whitespace (Join with "" instead of " ")
        #    This fixes the issue where "ต้อง\nทำ" became "ต้อง ทำ" matching against "ต้องทำ"
        return "".join(text.split()).lower()

    def extract_base_id(self, section_text):
        if not section_text: return ""
        return self.normalize_numerals(str(section_text).split('_')[0])

    # --- MATCHING LOGIC ---
    def is_match(self, target, chunk):
        d_type = str(target['doc_type']).strip()
        
        if d_type == "ระเบียบ":
            target_sec = self.extract_base_id(target['section'])
            chunk_sec = self.extract_base_id(chunk.get('section', chunk.get('id', '')))
            return target_sec == chunk_sec
        else:
            # Normalize BOTH sides tightly
            target_txt = self.normalize_text(target['context'])
            
            chunk_content = chunk.get('text') or chunk.get('context') or ""
            chunk_txt = self.normalize_text(chunk_content)
            
            if not target_txt or not chunk_txt: return False
            
            # Fuzzy Match
            return target_txt in chunk_txt or chunk_txt in target_txt

    # --- EVALUATION RUNNER ---
    async def run_and_save(self, input_file, output_file="detailed_eval_report.csv"):
        retriever = Retriever()
        data = get_processed_data(input_file)
        
        final_rows = []
        print(f"Starting evaluation on {len(data)} questions...")

        for item in data:
            q = item['question']
            targets = item['targets']
            
            # 1. Retrieve
            retrieved = await retriever.retrieve(user_query=q, search_date="2025-10-01")
            
            # 2. Prepare Top 3 Texts
            top_1_txt = retrieved[0].get('text', '') if len(retrieved) > 0 else ""
            top_2_txt = retrieved[1].get('text', '') if len(retrieved) > 1 else ""
            top_3_txt = retrieved[2].get('text', '') if len(retrieved) > 2 else ""

            # 3. Calculate Metrics (Top 5)
            top_5 = retrieved[:5]
            hits = []
            found_indices = set()
            
            for chunk in top_5:
                is_hit = False
                for t_idx, t in enumerate(targets):
                    if self.is_match(t, chunk):
                        is_hit = True
                        found_indices.add(t_idx)
                hits.append(1 if is_hit else 0)

            # 4. Metrics
            hit_rate = 1 if sum(hits) > 0 else 0
            
            mrr = 0
            for i, h in enumerate(hits):
                if h == 1:
                    mrr = 1 / (i + 1)
                    break
            
            recall = len(found_indices) / len(targets) if targets else 0

            # 5. Save Row
            final_rows.append({
                "Question": q,
                "Top_1_Text": top_1_txt,
                "Top_2_Text": top_2_txt,
                "Top_3_Text": top_3_txt,
                "Context": " | ".join([t['context'][:100] for t in targets]),
                "Section": " | ".join([t['section'] for t in targets]),
                "Doc_Name": " | ".join([t['doc_name'] for t in targets]),
                "Doc_Type": " | ".join([t['doc_type'] for t in targets]),
                "Hit_Rate": hit_rate,
                "MRR": mrr,
                "Recall": recall
            })

        df = pd.DataFrame(final_rows)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print("\n" + "="*30)
        print(f"DONE. Saved to {output_file}")
        print(f"Hit Rate: {df['Hit_Rate'].mean():.4f}")
        print(f"MRR:      {df['MRR'].mean():.4f}")
        print("="*30)

if __name__ == "__main__":
    evaluator = RAGEvaluator()
    # Ensure this matches your local file path
    asyncio.run(evaluator.run_and_save("test/Evalaution_matrix.csv"))