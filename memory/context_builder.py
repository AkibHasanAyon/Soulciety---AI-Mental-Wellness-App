# memory/context_builder.py
"""
Builds the memory context block to inject into the AI system prompt.
Combines structured DB memories + vector search results + conversation summaries.
"""
import logging
from .models import UserMemory, ConversationSummary
from .vector_store import search_memories

logger = logging.getLogger(__name__)

# Category display labels
CATEGORY_LABELS = {
    'identity': 'Personal Identity',
    'family': 'Family & Relationships',
    'career': 'Career & Work',
    'spiritual': 'Spiritual Journey',
    'emotional': 'Emotional Landscape',
    'exercises': 'Practices & Exercises',
    'patterns': 'Communication Patterns',
}


def build_memory_context(user, current_message=""):
    """
    Build a complete memory context string to inject into the system prompt.

    Args:
        user: CustomUser instance
        current_message: The current user message (for vector search relevance)

    Returns:
        String with formatted memory context, or empty string if no memories exist
    """
    sections = []

    # ── 1. Structured User Memories from DB ──
    structured_block = _build_structured_memory(user)
    if structured_block:
        sections.append(structured_block)

    # ── 2. Recent Conversation Summaries ──
    summary_block = _build_recent_summaries(user)
    if summary_block:
        sections.append(summary_block)

    # ── 3. Semantically Relevant Past Memories (Vector Search) ──
    if current_message:
        vector_block = _build_vector_memories(user, current_message)
        if vector_block:
            sections.append(vector_block)

    if not sections:
        return ""

    context = "\n\n".join(sections)
    return f"\n\n== USER MEMORY (use naturally, never quote this section) ==\n{context}\n== END USER MEMORY =="


def _build_structured_memory(user):
    """Build the structured memory block from UserMemory rows."""
    memories = UserMemory.objects.filter(
        user=user, is_active=True
    ).order_by('category', '-updated_at')

    if not memories.exists():
        return None

    # Group by category
    grouped = {}
    for mem in memories:
        if mem.category not in grouped:
            grouped[mem.category] = []
        grouped[mem.category].append(mem)

    lines = ["📋 What you know about this person:"]
    for category, items in grouped.items():
        label = CATEGORY_LABELS.get(category, category.title())
        lines.append(f"\n{label}:")
        for item in items:
            # Format key nicely: "children" → "Children"
            key_display = item.key.replace('_', ' ').title()
            lines.append(f"  - {key_display}: {item.value}")

    return "\n".join(lines)


def _build_recent_summaries(user, max_summaries=3):
    """Build summary block from recent conversation summaries."""
    summaries = ConversationSummary.objects.filter(
        user=user
    ).order_by('-updated_at')[:max_summaries]

    if not summaries.exists():
        return None

    lines = ["📝 Recent conversation context:"]
    for summary in summaries:
        emotional = f" (Mood: {summary.emotional_state})" if summary.emotional_state else ""
        lines.append(f"  - {summary.summary_text}{emotional}")

    return "\n".join(lines)


def _build_vector_memories(user, query_text, n_results=3):
    """Build relevant past memories block from vector search."""
    try:
        results = search_memories(user.id, query_text, n_results=n_results)

        if not results:
            return None

        # Filter out low-relevance results (high distance = low relevance)
        # ChromaDB distances: lower = more similar
        relevant = [r for r in results if r.get('distance', 1.0) < 1.5]

        if not relevant:
            return None

        lines = ["💡 Relevant past insights:"]
        for r in relevant:
            lines.append(f"  - {r['document']}")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Vector memory retrieval failed: {e}")
        return None
