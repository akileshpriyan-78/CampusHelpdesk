from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss
import pickle

# Folder containing college documents
DOCUMENT_FOLDER = Path("rag/documents")

documents = []

# Read all text files
for file in DOCUMENT_FOLDER.glob("*.txt"):
    text = file.read_text(encoding="utf-8")

    # Split document into smaller sections
    chunks = [
        chunk.strip()
        for chunk in text.split("\n\n")
        if chunk.strip()
    ]

    documents.extend(chunks)

print(f"Loaded {len(documents)} document chunks.")

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Convert text into vectors
embeddings = model.encode(documents)

# Create FAISS index
dimension = embeddings.shape[1]

index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

# Save vector database
faiss.write_index(index, "rag/faiss.index")

# Save document text
with open("rag/documents.pkl", "wb") as f:
    pickle.dump(documents, f)

print("RAG database created successfully!")
