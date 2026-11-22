# Text Splitter: Breaks long documents into coherent semantic chunks before generating embeddings.
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from app.dependencies.embedding_manager import EmbeddingManager
from fastapi import Request


def split_documents(document,embeddings:EmbeddingManager, chunk_size=600, chunk_overlap=200):
    """Splits documents semantically where embedding distance indicates a natural topic boundary."""
    # splitter = RecursiveCharacterTextSplitter(
    #     chunk_size=chunk_size,
    #     chunk_overlap=chunk_overlap,
    #     length_function=len,
    #     separators=["\n\n", "\n", ".", "!", "?", " ", ""]

    # )
    
    splitter = SemanticChunker(
        embeddings=embeddings,
        breakpoint_threshold_type="percentile",  # splits where meaning changes most
        breakpoint_threshold_amount=95           # higher = fewer but bigger chunks
    )
    
    # "percentile"	Split at the top X% biggest meaning jumps	✅ General use (start here)
    # "standard_deviation"	Split when jump is unusually large	Long dense documents
    # "interquartile"	Statistical middle-ground	Mixed content

    split_docs = splitter.split_documents(document)
    print(f"{len(document)} splitted into {len(split_docs)} chunks")

    # example if needed
    if split_docs:
        print(f"\nExample chunk:")
        print(f"Content: {split_docs[0].page_content[:200]}...")
        print(f"Metadata: {split_docs[0].metadata}")

    [doc.page_content for doc in split_docs]




    return split_docs
