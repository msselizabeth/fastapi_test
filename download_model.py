"""Download/cache the local model during deployment, before serving requests."""
from chunking import load_model

if __name__ == "__main__":
    load_model()
    print("Semantic chunking model ready.")
