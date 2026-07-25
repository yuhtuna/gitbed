import logging
# pyrefly: ignore [missing-import]
from langgraph.graph import END, START, StateGraph

from gitbed.nodes import generate_patch, open_pr, verify_patch
from gitbed.state import AgentState

logger = logging.getLogger(__name__)


def route_verification(state: AgentState) -> str:
    error_log = state.get("error_log", "")
    attempts = state.get("attempts", 0)

    if error_log:
        if attempts < 3:
            logger.info(f"Routing to retry patch generation (attempt {attempts}/3)")
            return "generate_patch"
        logger.error(f"Routing to END: max attempts reached ({attempts}/3)")
        return END

    logger.info("Routing to open_pr")
    return "open_pr"


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("generate_patch", generate_patch)
    workflow.add_node("verify_patch", verify_patch)
    workflow.add_node("open_pr", open_pr)

    workflow.add_edge(START, "generate_patch")
    workflow.add_edge("generate_patch", "verify_patch")

    workflow.add_conditional_edges(
        "verify_patch",
        route_verification,
        {
            "generate_patch": "generate_patch",
            "open_pr": "open_pr",
            END: END,
        },
    )

    workflow.add_edge("open_pr", END)

    return workflow.compile()
