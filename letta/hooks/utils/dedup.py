"""
Memory deduplication utilities.

Uses simple similarity matching to avoid storing duplicate memories.
"""

import re
from typing import Optional


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.

    - Lowercase
    - Collapse whitespace
    - Remove punctuation
    - Strip

    Args:
        text: Input text

    Returns:
        Normalized text
    """
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def jaccard_similarity(text1: str, text2: str) -> float:
    """
    Calculate Jaccard similarity between two texts.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity score between 0 and 1
    """
    words1 = set(normalize_text(text1).split())
    words2 = set(normalize_text(text2).split())

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union)


def is_duplicate(
    new_text: str,
    existing_texts: list[str],
    threshold: float = 0.85,
) -> Optional[str]:
    """
    Check if new text is a duplicate of any existing texts.

    Args:
        new_text: Text to check
        existing_texts: List of existing texts to compare against
        threshold: Similarity threshold (0-1). Default 0.85.

    Returns:
        The matching existing text if duplicate, None otherwise
    """
    for existing in existing_texts:
        similarity = jaccard_similarity(new_text, existing)
        if similarity >= threshold:
            return existing
    return None


def deduplicate_memories(
    memories: list[dict],
    content_key: str = "content",
    threshold: float = 0.85,
) -> list[dict]:
    """
    Remove duplicate memories from a list.

    Args:
        memories: List of memory dicts
        content_key: Key containing the text content
        threshold: Similarity threshold (0-1)

    Returns:
        Deduplicated list of memories
    """
    result = []
    seen_texts = []

    for memory in memories:
        content = memory.get(content_key, "")
        if not content:
            continue

        if not is_duplicate(content, seen_texts, threshold):
            result.append(memory)
            seen_texts.append(content)

    return result


def find_similar(
    query: str,
    texts: list[str],
    threshold: float = 0.3,
    limit: int = 5,
) -> list[tuple[str, float]]:
    """
    Find texts similar to query.

    Args:
        query: Search query
        texts: List of texts to search
        threshold: Minimum similarity threshold
        limit: Maximum results to return

    Returns:
        List of (text, similarity_score) tuples, sorted by similarity
    """
    results = []

    for text in texts:
        similarity = jaccard_similarity(query, text)
        if similarity >= threshold:
            results.append((text, similarity))

    # Sort by similarity descending
    results.sort(key=lambda x: x[1], reverse=True)

    return results[:limit]
