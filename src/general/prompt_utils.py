"""Prompt construction utilities shared across pipeline stages."""

from pathlib import Path


def get_repo_root() -> Path:
    """Get repository root directory."""
    return Path(__file__).parent.parent.parent


def load_prompt_template(prompt_path: str) -> str:
    """
    Load a prompt template file.

    Args:
        prompt_path: Path to prompt file (relative to repo root or absolute)

    Returns:
        Prompt template text

    Raises:
        FileNotFoundError: If prompt file not found
    """
    path = Path(prompt_path)

    # If relative path, resolve from repo root
    if not path.is_absolute():
        path = get_repo_root() / path

    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    return path.read_text(encoding="utf-8")


def build_full_prompt(
    universal_prefix: str,
    problem_text: str,
    output_format: str,
    cautionary_suffix: str = "",
    problem_data: dict = None
) -> str:
    """
    Build complete prompt by combining components.

    Args:
        universal_prefix: Universal CSP prefix template
        problem_text: Specific problem instance
        output_format: Task-specific output format instructions
        cautionary_suffix: Optional cautionary suffix to append
        problem_data: Optional problem data dict (for PDDL tasks with groundtruth info)

    Returns:
        Complete prompt with placeholders replaced and optional suffix
    """
    # Replace {PROBLEM} placeholder in prefix
    prompt_with_problem = universal_prefix.replace("{PROBLEM}", problem_text)

    # For PDDL tasks, replace additional placeholders if problem_data is provided
    if problem_data and "{GROUNDTRUTH_PROBLEM_PDDL}" in universal_prefix:
        groundtruth_pddl = problem_data.get("groundtruth_problem_pddl", "")
        domain_description = problem_data.get("domain_description", "")
        problem_description = problem_data.get("problem_description", "")

        prompt_with_problem = prompt_with_problem.replace("{GROUNDTRUTH_PROBLEM_PDDL}", groundtruth_pddl)
        prompt_with_problem = prompt_with_problem.replace("{DOMAIN_DESCRIPTION}", domain_description)
        prompt_with_problem = prompt_with_problem.replace("{PROBLEM_DESCRIPTION}", problem_description)

    # Append output format instructions
    full_prompt = f"{prompt_with_problem}\n\n{output_format}"

    # Append cautionary suffix if provided
    if cautionary_suffix and cautionary_suffix.strip():
        full_prompt = f"{full_prompt}\n\n{cautionary_suffix}"

    return full_prompt


def get_task_prompts(task: str) -> tuple[str, str]:
    """
    Get prompt file paths for a task.

    Args:
        task: Task name (calendar, meeting, zebralogic, blocksworld)

    Returns:
        Tuple of (universal_prefix_path, output_format_path)

    Raises:
        ValueError: If task is unknown
    """
    # Map tasks to their language and output format
    task_config = {
        "calendar": ("python", "prompts/formats/calendar_output_format.txt"),
        "meeting": ("python", "prompts/formats/meeting_output_format.txt"),
        "zebralogic": ("z3", "prompts/formats/zebralogic_output_format.txt"),
        "blocksworld": ("pddl", "prompts/formats/blocksworld_output_format.txt"),
    }

    if task not in task_config:
        raise ValueError(f"Unknown task: {task}. Choose from: {list(task_config.keys())}")

    language, output_format_path = task_config[task]
    universal_prefix_path = f"prompts/prefix/universal_csp_prefix_{language}.txt"

    return universal_prefix_path, output_format_path
