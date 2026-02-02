import pandas as pd

from app.chatbot.chatbot import Chatbot



def normalize_text(text):
    """
    Cleans text to ensure fair comparison:
    - Removes extra whitespaces and newlines
    - Converts to lowercase
    - Removes Thai 'zero-width' characters if any
    """
    if not isinstance(text, str):
        return ""
    return " ".join(text.split()).strip().lower()

def evaluate_by_text(qa_csv_path, retrieval_results_df, k=5):
    # 1. Load Ground Truth
    df_qa = pd.read_csv(qa_csv_path)
    df_qa['question'] = df_qa['question'].ffill()
    
    gt_map = {}
    for q, group in df_qa.groupby('question'):
        gt_map[q] = [normalize_text(txt) for txt in group['context'].tolist() if pd.notna(txt)]

    # 3. Compare with Retrieval Results
    eval_rows = []
    for _, row in retrieval_results_df.iterrows():
        q = row['question']
        if q not in gt_map: continue
        
        target_texts = gt_map[q]
        # Normalize the text retrieved by your RAG
        retrieved_texts = [normalize_text(c.get('text', '')) for c in row['retrieved_chunks'][:k]]
        
        # --- METRICS CALCULATION ---
        # Hit Rate: Was at least one correct chunk text found in top K?
        hit = 1 if any(any(t_text in r_text or r_text in t_text for r_text in retrieved_texts) 
                       for t_text in target_texts) else 0
        
        # MRR: Position of the first matching text
        rr = 0
        for i, r_text in enumerate(retrieved_texts):
            if any(t_text in r_text or r_text in t_text for t_text in target_texts):
                rr = 1 / (i + 1)
                break
        
        eval_rows.append({"question": q, "hit_rate": hit, "mrr": rr})

    return pd.DataFrame(eval_rows)


if __name__ == "__main__":
    chatbot = Chatbot()
    chatbot.answer_question()