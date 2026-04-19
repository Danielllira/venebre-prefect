from __future__ import annotations

import subprocess
import sys
from pathlib import Path

DEPLOY_BRANCHES = {
    "dev": "dev",
    "main": "prod",
}

PIPELINE_TYPES = {"extract", "migrate", "reports"}

GLOBAL_PATHS = (
    "pipelines/utils/",
    "pipelines/constants.py",
)


def run_command(command: list[str]) -> str:
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_current_branch() -> str:
    return run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])


def get_changed_files() -> list[str]:
    """
    Detecta arquivos alterados entre o commit atual e o anterior.
    """
    try:
        output = run_command(["git", "diff", "--name-only", "HEAD^", "HEAD"])
    except subprocess.CalledProcessError:
        return []

    return [line.strip() for line in output.splitlines() if line.strip()]


def should_deploy(branch: str) -> bool:
    return branch in DEPLOY_BRANCHES


def should_redeploy_all(changed_files: list[str]) -> bool:
    return any(
        changed_file.startswith(global_path)
        for changed_file in changed_files
        for global_path in GLOBAL_PATHS
    )


def list_all_pipeline_dirs() -> list[Path]:
    pipeline_dirs: list[Path] = []

    for pipeline_type in PIPELINE_TYPES:
        type_dir = Path("pipelines") / pipeline_type
        if not type_dir.exists():
            continue

        for pipeline_dir in type_dir.iterdir():
            if pipeline_dir.is_dir():
                pipeline_dirs.append(pipeline_dir)

    return sorted(pipeline_dirs)


def get_changed_pipeline_dirs(changed_files: list[str]) -> list[Path]:
    pipeline_dirs: set[Path] = set()

    for changed_file in changed_files:
        path = Path(changed_file)
        parts = path.parts

        if len(parts) < 4:
            continue

        if parts[0] != "pipelines":
            continue

        if parts[1] not in PIPELINE_TYPES:
            continue

        pipeline_dir = Path(*parts[:3])
        pipeline_dirs.add(pipeline_dir)

    return sorted(pipeline_dirs)


def get_environment_from_branch(branch: str) -> str:
    return DEPLOY_BRANCHES[branch]


def main() -> int:
    branch = get_current_branch()
    changed_files = get_changed_files()

    print(f"Current branch: {branch}")

    if not should_deploy(branch):
        print("Branch is not deployable. Skipping deployment.")
        return 0

    env = get_environment_from_branch(branch)
    print(f"Target environment: {env}")

    if not changed_files:
        print("No changed files detected.")
        return 0

    print("Changed files:")
    for changed_file in changed_files:
        print(f" - {changed_file}")

    if should_redeploy_all(changed_files):
        pipeline_dirs = list_all_pipeline_dirs()
        print("Global/shared change detected. Redeploying all pipelines.")
    else:
        pipeline_dirs = get_changed_pipeline_dirs(changed_files)

    if not pipeline_dirs:
        print("No pipeline directories detected for deployment.")
        return 0

    print("Pipelines selected for deployment:")
    for pipeline_dir in pipeline_dirs:
        print(f" - {pipeline_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())