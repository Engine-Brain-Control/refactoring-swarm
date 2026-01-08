from typing import TypedDict, List, Dict, Any, Optional

class SwarmState(TypedDict):
    target_dir: str
    files: List[str]
    current_file_index: int
    current_file_path: str
    current_file_content: str
    pylint_report: str
    refactoring_plan: str
    test_results: Dict[str, Any]
    iteration_count: int
    max_iterations: int
    status: str
    messages: List[str]
    cooldown_seconds: int
    disable_llm: bool
    output_mode: str
    output_dir: str
    results: List[Dict[str, Any]]
