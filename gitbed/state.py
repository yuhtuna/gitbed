from typing_extensions import TypedDict


class AgentState(TypedDict):
    diff_data: dict
    original_code: str
    updated_code: str
    error_log: str
    attempts: int
    pr_url: str
