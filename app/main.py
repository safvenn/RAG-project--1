# Entry point: starts the FastAPI web server and initializes the RAG backend services.
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.routers.file_upload_routes import router as file_upload_router
from app.routers.chat_routers import router as chat_routers
from app.dependencies.embedding_manager import EmbeddingManager
from app.dependencies.vector_store import Vector_Store
from app.dependencies.rag_retriever import RAGRetriver
from langchain_groq import ChatGroq
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
load_dotenv()

from app.dependencies.reranker_services import RerankerManager
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")

# Lifespan manager: runs once on server startup to initialize AI models and vector database.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load ChromaDB vector store, embedding model, CrossEncoder reranker, and Groq LLM
    print("Application starting...")
    
    app.state.vector_store = Vector_Store()
    app.state.embedding_manager = EmbeddingManager()
    app.state.reranker = RerankerManager()
    app.state.llm = ChatGroq(
            model_name='openai/gpt-oss-120b',
            api_key=GROQ_API_KEY,
            temperature=0.1,
            
        )

    yield

    # Shutdown: Clean up resources and reset shared state
    print("Application shutting down...")
    app.state.vector_store = None
    app.state.embedding_manager = None
    app.state.reranker = None
    app.state.llm = None


app = FastAPI(lifespan=lifespan)

# Directories: Ensure required storage folders exist for uploads, vectors, and frontend
VECTORSTORE_DIR = Path("vectorstore")
UPLOAD_DIR = Path("uploads")
FRONTEND_DIR = Path("frontend")

UPLOAD_DIR.mkdir(exist_ok=True)
VECTORSTORE_DIR.mkdir(exist_ok=True)

# CORS: Allows frontend web clients (e.g. localhost browsers) to make requests to this API
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers: Register endpoints for file management (/file) and question-answering (/chat)
app.include_router(file_upload_router)
app.include_router(chat_routers)

# Serve frontend: Mounts static files and serves index.html to user browsers
if FRONTEND_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

@app.get("/")
def home():
    # Serves the main web dashboard when accessing the base URL
    if FRONTEND_DIR.exists():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
    return {"msg": "running"}