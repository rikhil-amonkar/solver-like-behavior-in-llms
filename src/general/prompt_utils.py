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
    cautionary_suffix: str = ""
) -> str:
    """
    Build complete prompt by combining components.

    Args:
        universal_prefix: Universal CSP prefix template
        problem_text: Specific problem instance
        output_format: Task-specific output format instructions
        cautionary_suffix: Optional cautionary suffix to append

    Returns:
        Complete prompt with {PROBLEM} placeholder replaced and optional suffix
    """
    # Replace {PROBLEM} placeholder in prefix
    prompt_with_problem = universal_prefix.replace("{PROBLEM}", problem_text)

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
        task: Task name (calendar, meeting)

    Returns:
        Tuple of (universal_prefix_path, output_format_path)

    Raises:
        ValueError: If task is unknown
    """
    task_to_output_format = {
        "calendar": "prompts/calendar_output_format.txt",
        "meeting": "prompts/meeting_output_format.txt",
    }

    if task not in task_to_output_format:
        raise ValueError(f"Unknown task: {task}. Choose from: {list(task_to_output_format.keys())}")

    universal_prefix_path = "prompts/universal_csp_prefix.txt"
    output_format_path = task_to_output_format[task]

    return universal_prefix_path, output_format_path
