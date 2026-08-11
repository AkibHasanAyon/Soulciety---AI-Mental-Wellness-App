# memory/vector_store.py
"""
ChromaDB integration for semantic memory search.
Stores conversation memory embeddings and retrieves relevant past memories.
"""
import os
import logging
import chromadb
from django.conf import settings
from google import genai

logger = logging.getLogger(__name__)

# Gemini client for embeddings
_genai_client = None


def _get_genai_client():
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _genai_client


def _get_chroma_client():
    """Get or create a persistent ChromaDB client."""
    persist_dir = getattr(settings, 'CHROMA_PERSIST_DIR', os.path.join(settings.BASE_DIR, 'chroma_data'))
    os.makedirs(persist_dir, exist_ok=True)
    return chromadb.PersistentClient(path=persist_dir)


def _get_collection(user_id):
    """Get or create a ChromaDB collection for a specific user."""
    client = _get_chroma_client()
    collection_name = f"user_{user_id}_memories"
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"description": f"Memory embeddings for user {user_id}"}
    )


def _embed_text(text):
    """Generate embedding for a text string using Gemini."""
    try:
        client = _get_genai_client()
        result = client.models.embed_content(
            model=settings.MEMORY_EMBEDDING_MODEL,
            contents=text
        )
        return result.embeddings[0].values
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return None


def store_memory(user_id, memory_id, text, metadata=None):
    """
    Store a memory embedding in ChromaDB.

    Args:
        user_id: The user's ID
        memory_id: Unique ID for this memory (e.g., "memory_{pk}")
        text: The text to embed and store
        metadata: Optional dict of metadata (category, key, etc.)
    """
    try:
        embedding = _embed_text(text)
        if embedding is None:
            logger.warning(f"Skipping ChromaDB store for memory {memory_id} — embedding failed")
            return False

        collection = _get_collection(user_id)
        collection.upsert(
            ids=[str(memory_id)],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata or {}]
        )
        logger.info(f"Stored memory {memory_id} in ChromaDB for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"ChromaDB store failed for user {user_id}: {e}")
        return False


def search_memories(user_id, query_text, n_results=5):
    """
    Search for semantically similar memories for a user.

    Args:
        user_id: The user's ID
        query_text: The text to search against
        n_results: Maximum number of results to return

    Returns:
        List of dicts with 'document', 'metadata', 'distance' keys
    """
    try:
        collection = _get_collection(user_id)

        # Check if collection has any documents
        if collection.count() == 0:
            return []

        query_embedding = _embed_text(query_text)
        if query_embedding is None:
            return []

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count())
        )

        memories = []
        if results and results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                memories.append({
                    'document': doc,
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else None,
                })
        return memories
    except Exception as e:
        logger.error(f"ChromaDB search failed for user {user_id}: {e}")
        return []


def delete_user_memories(user_id):
    """Delete all memories for a user (e.g., account deletion)."""
    try:
        client = _get_chroma_client()
        collection_name = f"user_{user_id}_memories"
        client.delete_collection(collection_name)
        logger.info(f"Deleted all ChromaDB memories for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"ChromaDB delete failed for user {user_id}: {e}")
        return False
