"""Letta tool for searching files by semantic meaning using embeddings."""

import json
import os


def semantic_search(
    query: str,
    directory: str = ".",
    file_pattern: str = "*.py",
    top_k: int = 5,
    model: str = "text-embedding-3-small",
) -> str:
    """Search files by semantic meaning using OpenAI-compatible embeddings.

    Embeds the query and each file's content, then ranks by cosine similarity.
    Useful for finding relevant code or documentation when you don't know
    the exact keywords to search for.

    Args:
        query: Natural language description of what you're looking for.
        directory: Root directory to search in. Defaults to current directory.
        file_pattern: Glob pattern for files to include (e.g. "*.py", "*.md").
            Defaults to "*.py".
        top_k: Number of top results to return. Defaults to 5.
        model: Embedding model name. Defaults to "text-embedding-3-small".
            Works with any OpenAI-compatible embedding endpoint.

    Returns:
        JSON string with ranked results containing file path, similarity
        score, and a content preview, or an error message string on failure.
    """
    try:
        import requests
    except ImportError:
        return "Error: requests package not installed. pip install requests"

    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    if not api_key:
        return "Error: OPENAI_API_KEY environment variable not set."

    # Collect files matching the pattern
    import glob

    pattern = os.path.join(directory, "**", file_pattern)
    files = glob.glob(pattern, recursive=True)

    if not files:
        return f"No files matching '{file_pattern}' found in {directory}"

    # Read file contents (skip binary/large files)
    file_contents: list[tuple[str, str]] = []
    for fpath in files:
        try:
            if os.path.getsize(fpath) > 100_000:
                continue
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if content.strip():
                file_contents.append((fpath, content))
        except (OSError, PermissionError):
            continue

    if not file_contents:
        return f"No readable text files found matching '{file_pattern}' in {directory}"

    # Build texts to embed: query + all file contents
    texts = [query] + [content[:8000] for _, content in file_contents]

    # Get embeddings
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            f"{base_url}/embeddings",
            headers=headers,
            json={"model": model, "input": texts},
            timeout=60,
        )
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return "Error: Embedding API request timed out."
    except requests.exceptions.HTTPError:
        return f"Error from embedding API: {resp.status_code} - {resp.text[:300]}"
    except Exception as e:
        return f"Error calling embedding API: {e}"

    data = resp.json()
    embeddings = [item["embedding"] for item in data["data"]]

    query_emb = embeddings[0]
    file_embs = embeddings[1:]

    # Compute cosine similarities
    results: list[dict] = []
    for i, (fpath, content) in enumerate(file_contents):
        sim = _cosine_similarity(query_emb, file_embs[i])
        preview = content[:300].replace("\n", " ").strip()
        results.append({"file": fpath, "similarity": round(sim, 4), "preview": preview})

    results.sort(key=lambda x: x["similarity"], reverse=True)
    top_results = results[:top_k]

    return json.dumps(top_results, indent=2)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
