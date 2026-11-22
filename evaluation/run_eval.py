import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import re
import time
import json
import statistics
from typing import List, Dict, Any

from app.dependencies.embedding_manager import EmbeddingManager
from app.dependencies.vector_store import Vector_Store
from app.dependencies.reranker_services import RerankerManager
from app.dependencies.rag_retriever import RAGRetriver
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

# ── 1. Parse Questions from questions.txt.txt ─────────────────────────────────
def load_and_parse_questions(file_path: str) -> List[Dict[str, Any]]:
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Skip lines matching: Golden RAG Evaluation Resource • AI / Machine Learning Page n
    filtered_lines = []
    for line in text.splitlines():
        if re.search(r'Golden RAG Evaluation Resource\s*[•\x7f\-]?\s*AI\s*/\s*Machine Learning\s*Page\s*\d+', line, re.I):
            continue
        filtered_lines.append(line)

    cleaned_text = "\n".join(filtered_lines)

    # Regex to split questions Q01..Q25
    pattern = r'(Q\d{2}\..*?)(?=(?:Q\d{2}\.|\Z))'
    blocks = re.findall(pattern, cleaned_text, re.DOTALL)

    questions = []
    for block in blocks:
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if not lines:
            continue
        
        q_header = lines[0]
        qid_match = re.match(r'(Q\d{2})\.\s*(.*)', q_header)
        if not qid_match:
            continue
        qid = qid_match.group(1)
        q_text = qid_match.group(2).strip()

        # Find metadata lines
        ans_type = "Answerable"
        evidence_list = []
        expected_ans = ""
        scoring_note = ""

        # Parse Answerability and Evidence
        for line in lines:
            if line.startswith("Answerability:"):
                # Answerability: Answerable    Evidence: S01
                ans_match = re.search(r'Answerability:\s*([A-Za-z]+)', line)
                if ans_match:
                    ans_type = ans_match.group(1)
                ev_match = re.search(r'Evidence:\s*([^\n]+)', line)
                if ev_match:
                    raw_ev = ev_match.group(1).strip()
                    if raw_ev.lower() != "none":
                        # splits by ; or ,
                        evidence_list = [e.strip() for e in re.split(r'[;,]', raw_ev) if e.strip()]

        # Parse Expected answer and Scoring note
        exp_lines = []
        note_lines = []
        capture = None
        for line in lines[1:]:
            if line.startswith("Expected answer:"):
                capture = "exp"
                exp_lines.append(line.replace("Expected answer:", "").strip())
            elif line.startswith("Scoring note:"):
                capture = "note"
                note_lines.append(line.replace("Scoring note:", "").strip())
            elif capture == "exp":
                if not line.startswith("Scoring note:") and not line.startswith("Answerability:"):
                    exp_lines.append(line)
            elif capture == "note":
                note_lines.append(line)

        expected_ans = " ".join(exp_lines).strip()
        scoring_note = " ".join(note_lines).strip()

        questions.append({
            "qid": qid,
            "question": q_text,
            "answerability": ans_type,
            "evidence": evidence_list,
            "expected_answer": expected_ans,
            "scoring_note": scoring_note
        })

    return questions

# ── 2. Run Evaluation Pipeline ────────────────────────────────────────────────
def run_evaluation():
    print("=" * 70)
    print("Starting ECC RAG Evaluation Harness")
    print("=" * 70)

    # Parse questions
    q_file = r"c:\Desktop\RAG project -1\evaluation\questions.txt.txt"
    questions = load_and_parse_questions(q_file)
    print(f"Loaded {len(questions)} evaluation questions from {q_file}")

    # Initialize RAG components
    print("Initializing RAG components...")
    em = EmbeddingManager()
    vs = Vector_Store()
    reranker = RerankerManager()
    groq_api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("GROK_API_KEY")
    llm = ChatGroq(
        model_name="openai/gpt-oss-120b",
        api_key=groq_api_key,
        temperature=0.1
    )
    judge_llm = ChatGroq(
        model_name="openai/gpt-oss-120b",
        api_key=groq_api_key,
        temperature=0.0
    )

    retriever = RAGRetriver(
        embedding_manager=em,
        vectorstore=vs,
        reranker=reranker
    )

    prompt_template = PromptTemplate(
        input_variables=["context", "question"],
        template="""You are a helpful AI assistant. Use the following context to answer the question accurately and concisely.

Context:
{context}

Question: {question}

Answer: Provide a clear and informative answer based on the context above. If the context doesn't contain enough information to answer the question, say so. Also Provide Sources Where it from in the bottom."""
    )

    judge_template = PromptTemplate(
        input_variables=["question", "expected_answer", "scoring_note", "context", "generated_answer", "answerability"],
        template="""You are an expert impartial evaluation judge for a RAG system adhering to the official benchmark scoring rubric:

QUESTION: {question}
ANSWERABILITY: {answerability}
EXPECTED / GROUND TRUTH ANSWER: {expected_answer}
SCORING NOTE: {scoring_note}

RETRIEVED CONTEXT:
{context}

GENERATED ANSWER:
{generated_answer}

RUBRIC:
1. Answer Correctness (0 to 2):
   - 2: Correct. Contains key expected facts without material errors. (For unanswerable, correctly abstains or refutes false premise).
   - 1: Partially correct. Misses a key point, is vague, or contains minor errors.
   - 0: Incorrect, contradictory, or unsupported.
2. Faithfulness (0 to 2):
   - 2: Every material claim is grounded in the retrieved context. (If context was empty/insufficient and model abstained without hallucinating facts, score 2).
   - 1: Mostly grounded, minor unsupported detail.
   - 0: Hallucinated / contradicts context.
3. Abstention Handling (0 to 2 for unanswerable questions, N/A for answerable):
   - 2: Clearly states context does not contain info / refutes false premise without guessing.
   - 1: Expresses uncertainty but speculates.
   - 0: Confidently invents an answer.

Respond ONLY with valid JSON in this exact structure:
{{
  "correctness_score": <int 0-2>,
  "faithfulness_score": <int 0-2>,
  "abstention_score": <int 0-2 or null>,
  "correctness_reason": "<brief justification>",
  "faithfulness_reason": "<brief justification>"
}}"""
    )

    results = []
    print("\nRunning RAG and evaluating each question...\n")

    for idx, q in enumerate(questions):
        qid = q["qid"]
        q_text = q["question"]
        print(f"[{idx+1}/{len(questions)}] Processing {qid}: {q_text[:50]}...")

        # 1. Retrieval
        t_start_retrieval = time.time()
        retrieved_docs = retriever.retrive(q_text, initial_top_k=20, final_top_k=10)
        t_retrieval = time.time() - t_start_retrieval

        # Check evidence presence
        combined_context = "\n\n".join([d["content"] for d in retrieved_docs]) if retrieved_docs else ""
        evidence_found = {}
        for ev in q["evidence"]:
            # Check if section tag like S01 appears in retrieved text
            pattern = rf"\b{ev}\b"
            found = bool(re.search(pattern, combined_context, re.IGNORECASE))
            evidence_found[ev] = found

        if q["answerability"] == "Answerable":
            retrieval_success = 1 if (q["evidence"] and all(evidence_found.values())) else 0
        else:
            # Unanswerable questions: evidence retrieval is N/A or 1 if false premise source retrieved
            retrieval_success = 1 if (q["evidence"] and all(evidence_found.values())) else None

        # 2. Context formatting
        if retrieved_docs:
            formatted_context = "\n\n---\n\n".join(
                [
                    f"[Doc {doc['rank']}] (Score: {doc.get('rerank_score', doc['similarity_score']):.3f})\n{doc['content']}"
                    for doc in retrieved_docs
                ]
            )
        else:
            formatted_context = "No relevant context found in uploaded documents."

        # 3. Generation
        formatted_prompt = prompt_template.format(context=formatted_context, question=q_text)
        t_start_gen = time.time()
        try:
            gen_res = llm.invoke([formatted_prompt])
            generated_answer = gen_res.content
        except Exception as e:
            generated_answer = f"ERROR GENERATING: {e}"
        t_gen = time.time() - t_start_gen
        t_total = t_retrieval + t_gen

        # 4. Grading with Judge LLM
        judge_prompt = judge_template.format(
            question=q_text,
            expected_answer=q["expected_answer"],
            scoring_note=q["scoring_note"],
            context=formatted_context,
            generated_answer=generated_answer,
            answerability=q["answerability"]
        )
        try:
            judge_res = judge_llm.invoke([judge_prompt])
            # Parse JSON
            raw_judge = judge_res.content.strip()
            # extract json block
            json_match = re.search(r'\{.*\}', raw_judge, re.DOTALL)
            if json_match:
                judge_data = json.loads(json_match.group(0))
            else:
                judge_data = {
                    "correctness_score": 1,
                    "faithfulness_score": 1,
                    "abstention_score": 1 if q["answerability"] == "Unanswerable" else None,
                    "correctness_reason": "Failed to parse judge JSON",
                    "faithfulness_reason": "Failed to parse judge JSON"
                }
        except Exception as e:
            judge_data = {
                "correctness_score": 0,
                "faithfulness_score": 0,
                "abstention_score": 0 if q["answerability"] == "Unanswerable" else None,
                "correctness_reason": f"Judge error: {e}",
                "faithfulness_reason": f"Judge error: {e}"
            }

        # Handle rate limiting safety
        time.sleep(1.0)

        record = {
            "qid": qid,
            "question": q_text,
            "answerability": q["answerability"],
            "evidence": q["evidence"],
            "evidence_found": evidence_found,
            "retrieval_success": retrieval_success,
            "expected_answer": q["expected_answer"],
            "scoring_note": q["scoring_note"],
            "generated_answer": generated_answer,
            "retrieved_ranks": [
                {
                    "rank": d["rank"],
                    "score": round(d.get("rerank_score", d["similarity_score"]), 4),
                    "preview": d["content"][:120].replace("\n", " ")
                }
                for d in retrieved_docs
            ],
            "correctness_score": judge_data.get("correctness_score", 0),
            "faithfulness_score": judge_data.get("faithfulness_score", 0),
            "abstention_score": judge_data.get("abstention_score"),
            "correctness_reason": judge_data.get("correctness_reason", ""),
            "faithfulness_reason": judge_data.get("faithfulness_reason", ""),
            "latency": {
                "retrieval_sec": round(t_retrieval, 3),
                "generation_sec": round(t_gen, 3),
                "total_sec": round(t_total, 3)
            }
        }
        results.append(record)
        print(f"  -> Correctness: {record['correctness_score']}/2 | Faithfulness: {record['faithfulness_score']}/2 | RetrSuccess: {retrieval_success} | Total Latency: {t_total:.2f}s")

    # ── 3. Aggregate Metrics ──────────────────────────────────────────────────
    answerable = [r for r in results if r["answerability"] == "Answerable"]
    unanswerable = [r for r in results if r["answerability"] == "Unanswerable"]

    # Retrieval Success Rate on Answerable (20 questions)
    retrieval_hits = sum(r["retrieval_success"] for r in answerable if r["retrieval_success"] is not None)
    retrieval_rate = (retrieval_hits / len(answerable)) * 100.0 if answerable else 0

    # Answer Correctness
    corr_scores_ans = [r["correctness_score"] for r in answerable]
    perfect_corr_count = sum(1 for s in corr_scores_ans if s == 2)
    correctness_rate = (perfect_corr_count / len(answerable)) * 100.0 if answerable else 0
    mean_correctness = statistics.mean(corr_scores_ans) if corr_scores_ans else 0

    # Overall Correctness (all 25)
    all_corr_scores = [r["correctness_score"] for r in results]
    overall_mean_correctness = statistics.mean(all_corr_scores)

    # Faithfulness
    all_faith_scores = [r["faithfulness_score"] for r in results]
    mean_faithfulness = statistics.mean(all_faith_scores)
    faithfulness_rate = (mean_faithfulness / 2.0) * 100.0

    # Abstention Accuracy (Q21-Q25)
    abstention_scores = [r["abstention_score"] for r in unanswerable if r["abstention_score"] is not None]
    perfect_abstention = sum(1 for s in abstention_scores if s == 2)
    abstention_rate = (perfect_abstention / len(unanswerable)) * 100.0 if unanswerable else 0
    mean_abstention = statistics.mean(abstention_scores) if abstention_scores else 0

    # Latencies
    total_latencies = [r["latency"]["total_sec"] for r in results]
    ret_latencies = [r["latency"]["retrieval_sec"] for r in results]
    gen_latencies = [r["latency"]["generation_sec"] for r in results]

    summary = {
        "total_questions": len(results),
        "answerable_count": len(answerable),
        "unanswerable_count": len(unanswerable),
        "evidence_retrieval_rate_pct": round(retrieval_rate, 2),
        "answer_correctness_rate_pct": round(correctness_rate, 2),
        "mean_correctness_answerable": round(mean_correctness, 2),
        "overall_mean_correctness": round(overall_mean_correctness, 2),
        "faithfulness_rate_pct": round(faithfulness_rate, 2),
        "mean_faithfulness": round(mean_faithfulness, 2),
        "abstention_accuracy_pct": round(abstention_rate, 2),
        "mean_abstention_score": round(mean_abstention, 2),
        "latency_stats": {
            "total_median_sec": round(statistics.median(total_latencies), 3),
            "total_mean_sec": round(statistics.mean(total_latencies), 3),
            "total_p95_sec": round(sorted(total_latencies)[int(len(total_latencies)*0.95)], 3),
            "retrieval_mean_sec": round(statistics.mean(ret_latencies), 3),
            "generation_mean_sec": round(statistics.mean(gen_latencies), 3),
        }
    }

    output_data = {
        "summary": summary,
        "results": results
    }

    out_file = r"c:\Desktop\RAG project -1\evaluation\evaluation_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("EVALUATION COMPLETE - SUMMARY REPORT")
    print("=" * 70)
    print(f"Evidence Retrieval Rate (Recall@10) : {summary['evidence_retrieval_rate_pct']}% ({retrieval_hits}/{len(answerable)})")
    print(f"Answer Correctness Rate (Score=2)   : {summary['answer_correctness_rate_pct']}% ({perfect_corr_count}/{len(answerable)})")
    print(f"Mean Correctness (Answerable)       : {summary['mean_correctness_answerable']} / 2.0")
    print(f"Faithfulness Rate                   : {summary['faithfulness_rate_pct']}% (Mean: {summary['mean_faithfulness']} / 2.0)")
    print(f"Abstention Accuracy (Q21-Q25)       : {summary['abstention_accuracy_pct']}% (Mean: {summary['mean_abstention_score']} / 2.0)")
    print(f"Latency (Total Mean / Median / P95) : {summary['latency_stats']['total_mean_sec']}s / {summary['latency_stats']['total_median_sec']}s / {summary['latency_stats']['total_p95_sec']}s")
    print(f"Detailed results saved to: {out_file}")
    print("=" * 70)

if __name__ == "__main__":
    run_evaluation()
