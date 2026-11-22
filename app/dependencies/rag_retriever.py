# RAG Retriever: Orchestrates the 2-stage retrieval pipeline (Dense Vector Search + Reranking).
from app.dependencies.embedding_manager import EmbeddingManager
from app.dependencies.vector_store import Vector_Store
from app.dependencies.reranker_services import RerankerManager
from app.dependencies.RRF_ import reciprocal_rank_fusion
from fastapi import HTTPException
from typing import Optional, Any, List, Dict


class RAGRetriver:
    """Combines vector search, optional BM25 keyword search, and neural reranking for high precision."""

    def __init__(
        self,
        embedding_manager: EmbeddingManager,
        vectorstore: Vector_Store,
        reranker: Optional[RerankerManager] = None,
        bm25_index: Optional[Any] = None
    ):
        # Injects core retrieval components needed for candidate search and scoring
        self.embedding_manager = embedding_manager
        self.vectorstore = vectorstore
        self.reranker = reranker
        self.bm25_index = bm25_index

    def retrive(
        self,
        query: str,
        initial_top_k: int = 20,
        final_top_k: int = 5,
        threshold: Optional[float] = 0.0
    ):
        # Two-stage retrieval: broad candidate gathering followed by neural precision reranking
        print(f"Retrieving documents for query: '{query}'")
        print(f"Initial Top K: {initial_top_k}, Final Top K: {final_top_k}, Score threshold: {threshold}")

        if not query or not query.strip():
            return []

        # Stage 1: Broad retrieval from ChromaDB
        try:
            dense_docs = self.embedding_manager.search(
                query=query,
                threshold=threshold,
                top_k=initial_top_k,
                vectorstore=self.vectorstore
            )

            # Check if BM25 is available for hybrid retrieval
            if self.bm25_index:
                sparse_docs = self.bm25_index.search(query, top_k=initial_top_k)
                fused_candidates = reciprocal_rank_fusion(dense_docs, sparse_docs, k=60)
            else:
                fused_candidates = dense_docs

            if not fused_candidates:
                print("No matching documents found in vector db.")
                return []

            # Stage 2: Rerank candidates if reranker is provided
            if self.reranker:
                retrieved_docs = self.reranker.rerank(
                    query=query,
                    documents=fused_candidates,
                    top_n=final_top_k
                )
                print(f"Retrieved {len(retrieved_docs)} documents after reranking (Stage 2)")
                print(retrieved_docs)
            else:
                retrieved_docs = fused_candidates[:final_top_k]
            
            return retrieved_docs
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error during retrieval: {e}")
            raise HTTPException(detail=f"Error during retrieval: {e}", status_code=500)
