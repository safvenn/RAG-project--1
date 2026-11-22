# Embedding Manager: Converts human text into numerical vectors and queries ChromaDB.
import numpy as np
from sentence_transformers import SentenceTransformer
from fastapi import HTTPException
from typing import List, Any, Optional

from app.dependencies.vector_store import Vector_Store


class EmbeddingManager:
    """Manages the SentenceTransformer model to create semantic vector embeddings."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Initializes the model name and triggers initial loading
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
        # Downloads/loads the neural network into memory for fast embedding generation
        try:
            self.model = SentenceTransformer(self.model_name)
        except Exception as e:
            raise HTTPException(detail=f"Model Not loaded {e}", status_code=404)

    def genrate_embeddings(self, texts: List[str]) -> np.ndarray:
        # Encodes a list of text strings into normalized numerical vectors
        if self.model is None:
            raise HTTPException(detail="Model not loaded", status_code=404)

        embeddings = self.model.encode(texts, normalize_embeddings=True)
        print("Embedding manager works fine")
        return embeddings

    def embed_documents(self, texts):
        # LangChain compatible helper to return embeddings as a Python list
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def search(
        self,
        query: str,
        top_k: int = 20,
        threshold: Optional[float] = None,
        vectorstore: Optional[Vector_Store] = None
    ):
        # Queries ChromaDB collection using query embedding to find closest semantic matches
        print(f"Retrieving documents for query: '{query}'")
        print(f"Top K: {top_k}, Score threshold: {threshold}")

        if not query or not query.strip():
            return []

        # Stage 1: Broad retrieval from ChromaDB
        try:
            store = vectorstore or getattr(self, "vectorstore", None)
            if store is None:
                raise HTTPException(detail="Vector store not provided or initialized", status_code=500)

            query_embeddings = self.genrate_embeddings([query.strip()])[0]

            result = store.collection.query(
                query_embeddings=[query_embeddings.tolist()],
                n_results=top_k
            )

            retrieved_docs = []

            if result and result.get("documents") and result["documents"][0]:
                documents = result["documents"][0]
                metadatas = result["metadatas"][0] if result.get("metadatas") else [{} for _ in range(len(documents))]
                distances = result["distances"][0] if result.get("distances") else [0.0] * len(documents)
                ids = result["ids"][0] if result.get("ids") else [str(i) for i in range(len(documents))]

                space = (store.collection.metadata or {}).get("hnsw:space", "l2")

                for i, (doc_id, document, metadata, distance) in enumerate(zip(ids, documents, metadatas, distances)):
                    # Compute bounded similarity score based on distance space
                    if space == "cosine":
                        similarity_score = 1.0 - distance
                    else:
                        # For L2 distance (squared Euclidean), convert to bounded (0, 1] similarity
                        similarity_score = 1.0 / (1.0 + distance)

                    if threshold is not None and similarity_score < threshold:
                        continue

                    retrieved_docs.append({
                        "id": doc_id,
                        "content": document,
                        "metadata": metadata or {},
                        "similarity_score": similarity_score,
                        "distance": distance,
                        "rank": len(retrieved_docs) + 1
                    })

                print(f"Retrieved {len(retrieved_docs)} candidate documents (Stage 1)")

            return retrieved_docs
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(detail=f"Error retrieving documents: {str(e)}", status_code=404)
