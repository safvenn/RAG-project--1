# Chat Router: API endpoint that receives user questions and triggers retrieval-augmented generation.
from fastapi import APIRouter, HTTPException, Request
from langchain_core.prompts import PromptTemplate
from app.dependencies.rag_retriever import RAGRetriver
from app.services.chat_response_services import chat_response

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/")
def chat_router(prompt: str, request: Request):
    # Handles user queries: retrieves top relevant chunks and generates a grounded response
    embedding_manager = request.app.state.embedding_manager
    vector_store = request.app.state.vector_store
    llm = request.app.state.llm
    reranker = getattr(request.app.state, "reranker", None)

    rag_retriver = RAGRetriver(
        embedding_manager=embedding_manager,
        vectorstore=vector_store,
        reranker=reranker
    )

    retrieved_docs = rag_retriver.retrive(prompt, initial_top_k=20, final_top_k=4)

    if retrieved_docs:
        formatted_context = "\n\n---\n\n".join(
            [
                f"[Doc {doc['rank']}] (Score: {doc.get('rerank_score', doc['similarity_score']):.3f})\n{doc['content']}"
                for doc in retrieved_docs
            ]
        )
    else:
        formatted_context = "No relevant context found in uploaded documents."

    return chat_response(formatted_context,prompt)