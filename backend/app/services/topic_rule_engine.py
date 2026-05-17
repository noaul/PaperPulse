def evaluate_rule(
    rule_type: str,
    *,
    required_keyword_ids: list[int],
    exclude_keyword_ids: list[int],
    paper_keyword_scores: dict[int, float],
) -> bool:
    qualified = {
        int(keyword_id)
        for keyword_id, score in (paper_keyword_scores or {}).items()
        if float(score or 0) > 0
    }
    required = {int(keyword_id) for keyword_id in required_keyword_ids or []}
    excluded = {int(keyword_id) for keyword_id in exclude_keyword_ids or []}
    normalized_type = (rule_type or "OR").upper()

    if normalized_type == "AND":
        return bool(required) and required.issubset(qualified)
    if normalized_type == "NOT":
        return bool(required & qualified) and not bool(excluded & qualified)
    return bool(required & qualified)
