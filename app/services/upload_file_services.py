# Ingestion Service: Connects file loading, semantic chunking, vector embedding, and ChromaDB storage.
from fastapi import Request,HTTPException
from app.dependencies.fies_load import process_all_pdfs
from app.dependencies.text_splitter import split_documents
import shutil

def file_upload_services(directory:str,request:Request,filename:str):
    # Runs the ingestion pipeline: parses documents -> splits chunks -> generates embeddings -> saves to vector DB
    try:
        documents = process_all_pdfs(directory)
        embedding_manager = request.app.state.embedding_manager
    
        split_docs = split_documents(document=documents,embeddings=embedding_manager)
    
        texts = [doc.page_content for doc in split_docs]
    
        
        vector_store = request.app.state.vector_store
    
    
        embeddings = embedding_manager.genrate_embeddings(texts)
        
        vector_store.add_document(split_docs,embeddings,filename)
        return {
                    "msg":'Successfully added documents to vector store'
                }
    except Exception as e:
        shutil.rmtree(directory)
        raise HTTPException(detail=f"Faild to upload Vector DB{e}",status_code=400)