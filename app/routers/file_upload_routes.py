# File Management Router: API endpoints for uploading, listing, and removing knowledge documents.
import shutil
import datetime
from fastapi import APIRouter,File,UploadFile,HTTPException,Request
from pathlib import Path
from app.services.upload_file_services import file_upload_services
import shutil


router = APIRouter(
    prefix='/file',
    tags=['files']
)
VECTORSTORE_DIR = Path("vectorstore")

UPLOAD_DIR = Path("uploads")

@router.post("/upload")
async def upload_file(request:Request,file:UploadFile=File(...)):
    # Saves uploaded PDF/CSV to the uploads folder and starts the processing pipeline
    filename = str(file.filename)
    if any(p.is_file() for p in UPLOAD_DIR.rglob(filename)):
        raise HTTPException(detail="file already exits ",status_code = 404)

    upload_dir = UPLOAD_DIR / datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    upload_dir.mkdir(parents=True, exist_ok=False)

    file_path = upload_dir / Path(file.filename).name
    
    
    
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return file_upload_services(str(upload_dir),request,filename)
    except Exception as e:
        
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        file.file.close()
    
    
@router.get("/show")
def show_files():
    # Returns a list of all currently stored knowledge files on disk
    files = []
    directory = Path("uploads")

    for file in directory.rglob("*"):
        if file.is_file():
            print(file.name)
            files.append(file.name)
            
    return{
        "files":files,
        "total_files":len(files)
    }
    
@router.delete("/delete")
def delete_file(filename: str,request:Request):
    # Deletes the file from disk and deletes its chunk embeddings from ChromaDB
    vector_store = request.app.state.vector_store

    for p in UPLOAD_DIR.rglob(filename):
        if p.is_file():
            directory = p.parent
            try:
                vector_store.delete(filename)
                shutil.rmtree(directory)
            except Exception as e:
                raise HTTPException(detail={e},status_code=404)
            return {
                'msg':f"{filename} deleted sucessfullyy.."}
        else:
            return{
                "msg":"No file Found"
            }
    
    