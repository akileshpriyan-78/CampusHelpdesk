import faiss
import pickle
from sentence_transformers import SentenceTransformer

# Load the embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Load FAISS vector database
index = faiss.read_index("rag/faiss.index")

# Load document chunks
with open("rag/documents.pkl", "rb") as f:
    documents = pickle.load(f)


def search(query, k=3):
    # Convert user's question into a vector
    query_embedding = model.encode([query])

    # Search for the most similar document chunks
    distances, indices = index.search(query_embedding, k)

    results = []

    for i in indices[0]:
        if i < len(documents):
            results.append(documents[i])

    return results


# Test the search
if __name__ == "__main__":

    question = input("Enter your question: ")

    results = search(question)

    print("\nRelevant information:\n")

    for result in results:
        print(result)
        print("-" * 50)