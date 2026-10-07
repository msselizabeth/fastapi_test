"""Download/cache the local model during deployment, before serving requests."""
from chunking import MODEL_LOCK, load_model

if __name__ == "__main__":
    with MODEL_LOCK:
        load_model()
    print("Semantic chunking model ready.")
