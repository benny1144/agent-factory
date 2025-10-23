import os
import sys
from dotenv import load_dotenv

from langchain_community.document_loaders import TextLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

def main():
    """
    Main function to run the knowledge curation pipeline.
    This script takes a path to a source document, loads it,
    splits it into chunks, creates vector embeddings, and
    saves them to a local FAISS vector store.
    """
    
    # --- 0. Setup ---
    # Load environment variables (for the GOOGLE_API_KEY)
    load_dotenv()
    
    # Get the source document path from the command line argument
    if len(sys.argv) < 2:
        print("Error: You must provide a path to a source document.")
        print("Usage: python curate.py <path_to_document>")
        return
    
    source_document_path = sys.argv[1]
    
    if not os.path.exists(source_document_path):
        print(f"Error: File not found at '{source_document_path}'")
        return
        
    print(f"--- Starting curation for: {source_document_path} ---")

    # Define the path for our new vector store
    vector_store_path = "../../knowledge_base/vector_store/faiss_index"

    # --- 1. LOAD ---
    # Load the source document using a TextLoader
    print("Step 1: Loading document...")
    loader = TextLoader(source_document_path, encoding="utf-8")
    documents = loader.load()
    print(f"Successfully loaded {len(documents)} document(s).")

    # --- 2. SPLIT ---
    # Split the document into smaller, semantically meaningful chunks
    print("Step 2: Splitting document into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,  # Max size of each chunk
        chunk_overlap=100   # Overlap between chunks
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split document into {len(chunks)} chunks.")

    # --- 3. EMBED ---
    # Initialize the Google model for creating vector embeddings.
    # We use a dedicated embedding model for this.
    print("Step 3: Initializing embedding model...")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

    # --- 4. STORE ---
    # Create the vector store from the chunks and embeddings
    print("Step 4: Creating vector store... (This may take a moment)")
    db = FAISS.from_documents(chunks, embeddings)
    
    # Save the vector store locally
    db.save_local(vector_store_path)
    
    print("\n--- Curation Complete! ---")
    print(f"Vector store saved successfully at: {vector_store_path}")

if __name__ == "__main__":
    main()
