import os
from backend.app.config import settings

def check_documents():
    upload_dir = settings.UPLOAD_DIR
    vector_store_dir = settings.VECTOR_STORE_PATH
    
    print("Checking uploaded documents:")
    if os.path.exists(upload_dir):
        files = os.listdir(upload_dir)
        if files:
            print(f"Found {len(files)} files in upload directory:")
            for file in files:
                print(f"- {file}")
        else:
            print("No files found in upload directory")
    else:
        print("Upload directory does not exist")
    
    print("\nChecking vector store:")
    if os.path.exists(vector_store_dir):
        contents = os.listdir(vector_store_dir)
        if contents:
            print(f"Vector store exists with {len(contents)} files/directories")
            for item in contents:
                print(f"- {item}")
        else:
            print("Vector store is empty")
    else:
        print("Vector store directory does not exist")

if __name__ == "__main__":
    check_documents()