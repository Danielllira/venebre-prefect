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
    """
    Executa um comando no shell e retorna a saída em texto.

    Args:
        command: Lista com o comando e seus argumentos.

    Returns:
        Saída do comando sem espaços extras nas extremidades.
    """
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_current_branch() -> str:
    """
    Retorna o nome da branch atual do repositório.

    Args:
        None.

    Returns:
        Nome da branch atual.
    """
    return run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])


def get_changed_files() -> list[str]:
    """
    Retorna os arquivos alterados entre o commit atual e o anterior.

    Args:
        None.

    Returns:
        Lista com os caminhos dos arquivos alterados.
    """
    try:
        output = run_command(["git", "diff", "--name-only", "HEAD^", "HEAD"])
    except subprocess.CalledProcessError:
        return []

    return [line.strip() for line in output.splitlines() if line.strip()]


def should_deploy(branch: str) -> bool:
    """
    Indica se a branch atual deve gerar deploy.

    Args:
        branch: Nome da branch atual.

    Returns:
        True quando a branch é deployável, senão False.
    """
    return branch in DEPLOY_BRANCHES


def should_redeploy_all(changed_files: list[str]) -> bool:
    """
    Verifica se houve mudança em código global que exige redeploy total.

    Args:
        changed_files: Lista de arquivos alterados.

    Returns:
        True quando todos os pipelines devem ser redeployados.
    """
    return any(
        changed_file.startswith(global_path)
        for changed_file in changed_files
        for global_path in GLOBAL_PATHS
    )


def list_all_pipeline_dirs() -> list[Path]:
    """
    Lista todos os diretórios de pipeline disponíveis no repositório.

    Args:
        None.

    Returns:
        Lista ordenada com os diretórios de pipeline encontrados.
    """
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
    """
    Mapeia os pipelines impactados com base nos arquivos alterados.

    Args:
        changed_files: Lista de arquivos alterados.

    Returns:
        Lista ordenada com os diretórios de pipeline impactados.
    """
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
    """
    Retorna o ambiente correspondente para a branch informada.

    Args:
        branch: Nome da branch atual.

    Returns:
        Nome do ambiente associado à branch.
    """
    return DEPLOY_BRANCHES[branch]


def main() -> int:
    """
    Identifica quais pipelines devem ser deployados no ambiente atual.

    Args:
        None.

    Returns:
        Código de saída do processo.
    """
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