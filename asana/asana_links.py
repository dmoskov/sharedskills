#!/usr/bin/env python3
"""Resolve Asana URLs in field values to the names of what they link to.

In the Asana UI a pasted task, record or project URL renders as a chip with the
linked object's name. Through the API a text custom field returns only the raw
URL, so an agent sees an opaque GID. This module finds Asana URLs in text,
looks the objects up (via POST /batch, 10 actions per call, cached per run)
and reports each link as {"gid", "resource_type", "name", "url"}.

URL shapes recognized:
    https://app.asana.com/1/<ws>/record/<gid>
    https://app.asana.com/1/<ws>/project/<p>/task/<gid>   (and /1/<ws>/task/<gid>)
    https://app.asana.com/1/<ws>/project/<gid>[/list|/board|...]
    https://app.asana.com/1/<ws>/goal/<gid>, /1/<ws>/portfolio/<gid>
    https://app.asana.com/0/goal/<gid>, /0/portfolio/<gid>[/list]
    https://app.asana.com/0/<project>/<task>[/f], /0/0/<task>
    https://app.asana.com/0/<gid>[/]  (type not in the URL: project, record or
                                        a user's task list; tried in turn)
"""

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

BATCH_MAX_ACTIONS = 10

URL_PATTERN = re.compile(r"https://app\.asana\.com/[0-9]/[^\s<>()\"'\]]+")

# Typed path segments, newest URL scheme. The last one in a URL names the
# object (a task URL also names its project).
_TYPED_SEGMENT = re.compile(r"(record|task|project|goal|portfolio)/(\d+)")

# GET endpoint per resource type.
_ENDPOINTS = {
    "record": "records",
    "task": "tasks",
    "project": "projects",
    "goal": "goals",
    "portfolio": "portfolios",
}

# Types tried, in order, for a legacy /0/<gid> URL whose type isn't in the path.
_UNTYPED_ORDER = ("project", "record", "task")


def parse_asana_url(url: str) -> Optional[Tuple[str, Optional[str]]]:
    """(gid, resource_type) for an Asana object URL; resource_type None if the URL doesn't say."""
    match = re.match(r"https://app\.asana\.com/([01])/(.*)$", url.rstrip("/"))
    if not match:
        return None
    scheme, path = match.groups()
    parts = [p for p in path.split("/") if p]
    if scheme == "1":
        typed = _TYPED_SEGMENT.findall("/".join(parts[1:]))
        if typed:
            kind, gid = typed[-1]
            return gid, kind
        return None
    # Legacy /0/ scheme.
    if len(parts) >= 2 and parts[0] in ("goal", "portfolio") and parts[1].isdigit():
        return parts[1], parts[0]
    numeric = [p for p in parts[:2] if p.isdigit()]
    if len(numeric) == 2 and parts[0].isdigit() and parts[1].isdigit():
        # /0/<project or 0>/<task>
        return parts[1], "task"
    if parts and parts[0].isdigit() and parts[0] != "0":
        return parts[0], None
    return None


def find_asana_urls(text: Any) -> List[str]:
    """Asana object URLs in a string, in order, without duplicates."""
    if not isinstance(text, str) or "app.asana.com" not in text:
        return []
    found = []
    for url in URL_PATTERN.findall(text):
        url = url.rstrip(".,;:")
        if url not in found and parse_asana_url(url):
            found.append(url)
    return found


class LinkResolver:
    """Look up the objects behind Asana URLs, batched and cached for one run."""

    def __init__(self, client):
        self._client = client
        self._cache: Dict[Tuple[str, Optional[str]], Dict[str, Any]] = {}

    def resolve_urls(self, urls: Iterable[str]) -> Dict[str, Dict[str, Any]]:
        """{url: link} for every URL, resolving uncached objects in as few batch calls as possible."""
        parsed = {url: parse_asana_url(url) for url in urls}
        parsed = {url: key for url, key in parsed.items() if key}
        self._fetch([key for key in parsed.values() if key not in self._cache])
        return {url: dict(self._cache[key], url=url) for url, key in parsed.items()}

    def links_in(self, text: Any) -> List[Dict[str, Any]]:
        """Resolved links for each Asana URL in `text`."""
        urls = find_asana_urls(text)
        if not urls:
            return []
        resolved = self.resolve_urls(urls)
        return [resolved[u] for u in urls if u in resolved]

    def _fetch(self, keys: List[Tuple[str, Optional[str]]]) -> None:
        keys = list(dict.fromkeys(keys))
        if not keys:
            return
        # Each (gid, type) becomes one action; untyped GIDs try each type and
        # keep the first that answers.
        actions: List[Tuple[Tuple[str, Optional[str]], str]] = []
        for gid, kind in keys:
            for candidate in ([kind] if kind else _UNTYPED_ORDER):
                actions.append(((gid, kind), candidate))
        results: Dict[Tuple[str, Optional[str]], Dict[str, Any]] = {}
        from asana_client import AsanaError

        try:
            responses = self._client.batch_get(
                [f"/{_ENDPOINTS[candidate]}/{gid}" for (gid, _), candidate in actions],
                fields=["name"],
            )
        except AsanaError as e:  # a failed lookup leaves the URL; it never fails the command
            for key in keys:
                self._cache[key] = _unresolved(key, f"lookup failed: {e}")
            return
        for (key, candidate), response in zip(actions, responses):
            if key in results and results[key].get("name") is not None:
                continue
            status = response.get("status_code")
            body = response.get("body") or {}
            data = body.get("data") or {}
            if status == 200 and data.get("name") is not None:
                results[key] = {
                    "gid": key[0],
                    "resource_type": candidate,
                    "name": data["name"],
                }
            elif key not in results:
                results[key] = _unresolved(key, _reason(status, body, untyped=key[1] is None))
        self._cache.update(results)


def _reason(status: Optional[int], body: Dict[str, Any], untyped: bool) -> str:
    if untyped:
        return "unknown object type, or not found"
    if status == 403:
        return "no access"
    if status == 404:
        return "not found"
    message = ((body.get("errors") or [{}])[0]).get("message")
    return f"HTTP {status}" + (f": {message}" if message else "")


def _unresolved(key: Tuple[str, Optional[str]], reason: str) -> Dict[str, Any]:
    return {"gid": key[0], "resource_type": key[1], "name": None, "reason": reason}


def describe_link(link: Dict[str, Any]) -> str:
    """Human form of a resolved link: 'Name (record 123)' or the URL plus why it isn't named."""
    if link.get("name") is not None:
        return f"{link['name']} ({link['resource_type']} {link['gid']})"
    return f"{link['url']} ({link.get('reason', 'unresolved')})"


def annotate_fields(custom_fields: List[Dict[str, Any]], resolver: LinkResolver) -> None:
    """Add "links" to each custom field whose value contains Asana URLs (in place)."""
    pending = [f for f in custom_fields or [] if find_asana_urls(_raw_value(f))]
    if not pending:
        return
    resolver.resolve_urls(u for f in pending for u in find_asana_urls(_raw_value(f)))
    for field in pending:
        field["links"] = resolver.links_in(_raw_value(field))


def annotate_objects(objects: List[Dict[str, Any]], resolver: LinkResolver) -> None:
    """annotate_fields across many tasks or records with one round of batch lookups."""
    every_url = [
        u for obj in objects for f in obj.get("custom_fields") or [] for u in find_asana_urls(_raw_value(f))
    ]
    resolver.resolve_urls(every_url)
    for obj in objects:
        annotate_fields(obj.get("custom_fields") or [], resolver)


def display_with_links(field: Dict[str, Any]) -> Any:
    """The field's display value with each resolved Asana URL replaced by 'Name (type gid)'."""
    value = field.get("display_value")
    if not isinstance(value, str):
        return value
    for link in field.get("links") or []:
        value = value.replace(link["url"], describe_link(link))
    return value


def _raw_value(field: Dict[str, Any]) -> Any:
    return field.get("text_value") if field.get("text_value") is not None else field.get("display_value")
