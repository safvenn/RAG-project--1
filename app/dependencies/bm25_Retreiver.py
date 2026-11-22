# BM25 Sparse Index: Keyword-based ranking engine using Okapi BM25 for lexical matching.
from rank_bm25 import BM25Okapi
from typing import List,Dict,Any


class BM25Index:
    """Maintains tokenized corpus and computes BM25 relevance scores for exact keyword matching."""
    def __init__(self):
        self.corpus: List[Dict[str, Any]] = []
        self.bm25: BM25Okapi = None
    
    def build_index(self,documents:List[Dict[str, Any]]):
        """
        documents: list of dicts like [{"id": "...", "content": "...", "metadata": {...}}]
        """
        self.corpus = documents
        tokenized_corpus = [doc['content'].lower().split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        def search(self,query:str,top_k:int =20) ->List[Dict[str,Any]]:
            if not self.bm25 or self.corpus:
                return []
            tokenized_query = query.lower().split()
            scores = self.bm25.get_scores(tokenized_query)
            
            #pair documents with their bM25 score
            
            score_docs = list(zip(self.corpus , scores))
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            result = []
            
            for rank,(doc,score) in enumerate(score_docs[:top_k],start=1):
                doc_copy = doc.copy()
                doc_copy["sparse_rank"] = rank
                doc_copy["sparse_score"] = float(score)
                results.append(doc_copy)
            return result


