"""Pure functions for agent edits - no LLM/inference dependencies."""


def apply_edits(content: str, edits: list[dict]) -> str:
    """
    Apply find/replace edits in order. Each edit is {"find": "...", "replace": "..."}.
    Raises ValueError if any find string is not in content.
    """
    result = content
    for i, edit in enumerate(edits):
        find_str = edit.get("find")
        replace_str = edit.get("replace", "")
        if find_str is None:
            raise ValueError(f"Edit {i}: missing 'find' key")
        if find_str not in result:
            raise ValueError(f"Edit {i}: find not found: {find_str!r}")
        result = result.replace(find_str, replace_str, 1)  # Replace first occurrence only
    return result
