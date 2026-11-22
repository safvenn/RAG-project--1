# Neural Reranker: Stage-2 cross-encoder model that scores query-document pairs with high precision.
from sentence_transformers import CrossEncoder
from typing import List, Dict, Any

class RerankerManager:
    """Uses a CrossEncoder to perform deep semantic comparison and reorder retrieval candidates."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        'cross-encoder/ms-marco-MiniLM-L-6-v2' is fast, lightweight (~80MB),
        and highly accurate for passage ranking.
        Alternative for multi-lingual: 'BAAI/bge-reranker-base'
        """
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, documents: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        # Feeds (query, text) pairs directly into the cross-encoder and sorts by highest relevance score
        if not documents:
            return []

        # 1. Build [query, document_text] pairs
        pairs = [[query, doc["content"]] for doc in documents]

        # 2. Compute cross-encoder relevance scores
        scores = self.model.predict(pairs)

        # 3. Attach rerank score to each document
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = float(score)

        # 4. Sort documents descending by rerank score
        reranked_docs = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)

        # 5. Take the top_n items and update rank indices
        final_docs = reranked_docs[:top_n]
        for i, doc in enumerate(final_docs):
            doc["rank"] = i + 1

        return final_docs