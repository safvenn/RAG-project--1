# Document Loader: Reads and parses uploaded PDF and CSV files into LangChain document objects.
from pathlib import Path

from langchain_community.document_loaders import PyMuPDFLoader ,CSVLoader

## To load files

# .docx → Docx2txtLoader
# .pdf → PyPDFLoader
# .txt → TextLoader
# .csv → CSVLoader
# .xlsx → UnstructuredExcelLoader or Pandas


def process_all_pdfs(directory):
    """Scans the upload folder recursively and extracts text and metadata from PDF and CSV files."""
    all_doc = []
    pdf_dir = Path(directory)

    # find all PDF Files Recursively

    pdf_files = list(pdf_dir.glob("**/*.pdf"))
    csv_files = list(pdf_dir.glob("**/*.csv"))
    
    

    if pdf_files:

        for pdf_file in pdf_files:
            print(f"Processing {pdf_file.name}")
            try:

                loader = PyMuPDFLoader(str(pdf_file))
                documents = loader.load()

                # Add source information to metadata

                for doc in documents:
                    doc.metadata['source_file'] = pdf_file.name
                    doc.metadata['file_type'] = 'pdf'

                all_doc.extend(documents)
                print(f"  ✓ Loaded {len(documents)} pages")
            except Exception as e:
                print(f"  ✗ Error: {e}")
            
    
    ## FOR CSV FILES
    
    
    
    if csv_files:
      for csvfile in csv_files:
        
        try:
            loader = CSVLoader(str(csvfile))
            documents = loader.load()
            
            for doc in documents:
                doc.metadata['source_file'] = csvfile.name
                doc.metadata['file_type'] = 'csv'
                
            all_doc.extend(documents)
            print(f"  ✓ Loaded {len(documents)} pages")
        except Exception as e:
            print(f"  ✗- Error: {e}")
    print(f"\nTotal documents loaded: {len(all_doc)}")

    return all_doc



