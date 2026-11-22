# Vector Store: Handles persistent ChromaDB vector indexing, storage, and chunk deletion.
import uuid
from typing import Any, List
import numpy as np
import os
import chromadb
from fastapi import HTTPException
from pathlib import Path


UPLOAD_DIR =Path("vectorstore")
class Vector_Store:
        """Wrapper around ChromaDB for storing document text chunks, metadata, and embeddings."""
        def __init__(self, collection_name:str = 'documents',presist_directory:str = UPLOAD_DIR):
            # Configures storage directory and initializes the ChromaDB client
            self.collection_name = collection_name
            self.presist_directory = presist_directory
            self.client = None
            self.collection = None
            self._initialise_store()


        def _initialise_store(self):
            # Connects to ChromaDB on disk and opens or creates the embedding collection
            try:

                self.client = chromadb.PersistentClient(path=self.presist_directory)
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"description": "PDF document embeddings for RAG", "hnsw:space": "cosine"}
                )

            except Exception as e:
                raise HTTPException(status_code=400, detail=f"erorr on _initialise_store{str(e)}")

        def delete(self, filename: str):
            # Deletes all vector chunks that originated from the specified filename
            self.collection.delete(
                    where={"source": filename})
        
        
        def add_document(self,document:List[Any],embedings:np.ndarray,filename:str):
            # Adds document chunks, metadata, and their corresponding vector embeddings into ChromaDB
            if len(embedings) != len(document):
                raise HTTPException(status_code=400, detail="length of emebeddings and documents dont match!.....")
            ids = []
            metadatas = []
            documents_texts = []
            embeddings_list = []


            for i,(doc,embed) in enumerate(zip(document,embedings)):
                doc_id = f"doc_{uuid.uuid4().hex[:8]}_{i}"
                ids.append(doc_id)

                metadata = dict(doc.metadata)
                metadata['doc_index'] = i
                metadata['source'] = filename
                metadata['content_length'] = len(doc.page_content)

                metadatas.append(metadata)

                documents_texts.append(doc.page_content)

                embeddings_list.append(embed.tolist())

            try:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings_list,
                    metadatas=metadatas,
                    documents=documents_texts
                )
                print(f"Successfully added {len(document)} documents to vector store")
                print(f"Total documents in collection: {self.collection.count()}")

                
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"erorr on collection {str(e)}")



