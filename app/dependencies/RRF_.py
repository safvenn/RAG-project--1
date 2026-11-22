# Reciprocal Rank Fusion (RRF): Merges dense vector and sparse keyword search results fairly.
def reciprocal_rank_fusion(
    dense_results: List[Dict[str, Any]], 
    sparse_results: List[Dict[str, Any]], 
    k: int = 60
) -> List[Dict[str, Any]]:
    # Calculates 1 / (k + rank) for each document across both searches to produce a unified score
    fused_scores = {}
    doc_map = {}

    # Accumulate dense ranks
    for rank, doc in enumerate(dense_results, start=1):
        doc_id = doc["id"]
        doc_map[doc_id] = doc
        fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + (1.0 / (k + rank))

    # Accumulate sparse ranks
    for rank, doc in enumerate(sparse_results, start=1):
        doc_id = doc["id"]
        if doc_id not in doc_map:
            doc_map[doc_id] = doc
        fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + (1.0 / (k + rank))

    # Sort merged documents by fused RRF score
    reranked_docs = []
    for doc_id, score in sorted(fused_scores.items(), key=lambda x: x[1], reverse=True):
        doc = doc_map[doc_id]
        doc["rrf_score"] = score
        reranked_docs.append(doc)

    return reranked_docs