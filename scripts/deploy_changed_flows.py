from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

from prefect import Flow

DEPLOY_BRANCHES = {
    "dev": "dev",
    "main": "prod",
}

PIPELINE_TYPES = {"extract", "migrate", "reports"}

GLOBAL_PATHS = (
    "pipelines/utils/",
    "pipelines/constants.py",
    "tests/",
)

IMAGE_BY_ENV = {
    "dev": "us-south1-docker.pkg.dev/venebre-dev/venebre-prefect/runtime:dev",
    "prod": "us-south1-docker.pkg.dev/venebre-prod/venebre-prefect/runtime:prod",
}

PROJECT_BY_ENV = {
    "dev": "venebre-dev",
    "prod": "venebre-prod",
}

REGION_BY_ENV = {
    "dev": "us-south1",
    "prod": "us-south1",
}

SERVICE_ACCOUNT_BY_ENV = {
    "dev": "prefect-runner@venebre-dev.iam.gserviceaccount.com",
    "prod": "prefect-runner@venebre-prod.iam.gserviceaccount.com",
}

WORK_POOL_BY_ENV = {
    "dev": "venebre-cloud-run-dev",
    "prod": "venebre-cloud-run-prod",
}

TAGS_BY_ENV = {
    "dev": ["dev"],
    "prod": ["prod"],
}


def run_command(command: list[str]) -> str:
    """
    Executa um comando no shell e retorna a saída em texto.

    Args:
        command: Lista com o comando e seus argumentos.

    Returns:
        Saída do comando sem espaços extras.
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
    Retorna os arquivos alterados no último commit.

    Args:
        None.

    Returns:
        Lista de caminhos de arquivos alterados.
    """
    try:
        output = run_command(["git", "diff", "--name-only", "HEAD^", "HEAD"])
    except subprocess.CalledProcessError:
        return []

    return [line.strip() for line in output.splitlines() if line.strip()]


def should_deploy(branch: str) -> bool:
    """
    Valida se a branch atual deve publicar deployments.

    Args:
        branch: Nome da branch atual.

    Returns:
        True quando a branch é elegível para deploy.
    """
    return branch in DEPLOY_BRANCHES


def should_redeploy_all(changed_files: list[str]) -> bool:
    """
    Valida se mudanças compartilhadas exigem redeploy de todos os pipelines.

    Args:
        changed_files: Lista de arquivos alterados no commit atual.

    Returns:
        True quando todos os pipelines devem ser republicados.
    """
    return any(
        changed_file.startswith(global_path)
        for changed_file in changed_files
        for global_path in GLOBAL_PATHS
    )


def list_all_pipeline_dirs() -> list[Path]:
    """
    Lista todos os diretórios de pipeline que possuem flows.py.

    Args:
        None.

    Returns:
        Lista ordenada com os diretórios dos pipelines válidos.
    """
    pipeline_dirs: list[Path] = []

    for pipeline_type in PIPELINE_TYPES:
        type_dir = Path("pipelines") / pipeline_type
        if not type_dir.exists():
            continue

        for pipeline_dir in type_dir.iterdir():
            if not pipeline_dir.is_dir():
                continue

            if not (pipeline_dir / "flows.py").exists():
                continue

            pipeline_dirs.append(pipeline_dir)

    return sorted(pipeline_dirs)


def get_changed_pipeline_dirs(changed_files: list[str]) -> list[Path]:
    """
    Converte arquivos alterados em diretórios raiz de pipelines afetados.

    Args:
        changed_files: Lista de arquivos alterados no commit atual.

    Returns:
        Lista ordenada com os diretórios de pipelines afetados.
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

        if not (pipeline_dir / "flows.py").exists():
            continue

        pipeline_dirs.add(pipeline_dir)

    return sorted(pipeline_dirs)


def get_environment_from_branch(branch: str) -> str:
    """
    Converte a branch atual no ambiente de deploy correspondente.

    Args:
        branch: Nome da branch atual.

    Returns:
        Nome do ambiente.
    """
    return DEPLOY_BRANCHES[branch]


def build_module_name(pipeline_dir: Path) -> str:
    """
    Monta o nome do módulo Python de flows de um pipeline.

    Args:
        pipeline_dir: Diretório raiz do pipeline.

    Returns:
        Nome importável do módulo flows.py.
    """
    return ".".join((*pipeline_dir.parts, "flows"))


def get_flow_from_module(module_name: str) -> Flow:
    """
    Encontra o único flow deployável dentro de um módulo flows.

    Args:
        module_name: Nome do módulo Python a ser importado.

    Returns:
        Objeto Flow encontrado no módulo.

    Raises:
        ValueError: Quando nenhum ou mais de um Flow é encontrado.
    """
    module = importlib.import_module(module_name)

    flows = [value for value in vars(module).values() if isinstance(value, Flow)]

    if len(flows) == 0:
        raise ValueError(f"Nenhum Flow encontrado no módulo '{module_name}'.")

    if len(flows) > 1:
        raise ValueError(
            f"Mais de um Flow encontrado no módulo '{module_name}'. "
            "Mantenha apenas um flow deployável por flows.py."
        )

    return flows[0]


def build_deployment_name(flow_name: str, env: str) -> str:
    """
    Monta o nome final do deployment a partir do flow e do ambiente.

    Args:
        flow_name: Nome do flow no Prefect.
        env: Ambiente do deployment.

    Returns:
        Nome final do deployment.
    """
    if env == "dev":
        return f"{flow_name} - Dev"

    return flow_name


def deploy_flow(pipeline_dir: Path, env: str) -> None:
    """
    Publica o deployment de um flow no work pool correto.

    Importante:
        Este script assume como convenção do projeto que todo flow
        deployável aceita o parâmetro `env`.

    Args:
        pipeline_dir: Diretório raiz do pipeline.
        env: Ambiente de publicação do deployment.

    Returns:
        None.
    """
    module_name = build_module_name(pipeline_dir)
    flow = get_flow_from_module(module_name)
    deployment_name = build_deployment_name(flow.name, env)
    work_pool_name = WORK_POOL_BY_ENV[env]
    image = IMAGE_BY_ENV[env]
    project = PROJECT_BY_ENV[env]
    region = REGION_BY_ENV[env]
    service_account_name = SERVICE_ACCOUNT_BY_ENV[env]
    tags = TAGS_BY_ENV[env]
    parameters = {"env": env}
    job_variables = {
        "region": region,
        "service_account_name": service_account_name,
        "credentials": {"project": project},
    }

    print(f"[deploy_flow] pipeline_dir={pipeline_dir}")
    print(f"[deploy_flow] module_name={module_name}")
    print(f"[deploy_flow] flow_name={flow.name}")
    print(f"[deploy_flow] deployment_name={deployment_name}")
    print(f"[deploy_flow] work_pool_name={work_pool_name}")
    print(f"[deploy_flow] image={image}")
    print(f"[deploy_flow] project={project}")
    print(f"[deploy_flow] region={region}")
    print(f"[deploy_flow] service_account_name={service_account_name}")
    print(f"[deploy_flow] tags={tags}")
    print(f"[deploy_flow] parameters={parameters}")
    print(f"[deploy_flow] job_variables={job_variables}")

    flow.deploy(
        name=deployment_name,
        work_pool_name=work_pool_name,
        image=image,
        job_variables=job_variables,
        parameters=parameters,
        tags=tags,
        build=False,
        push=False,
    )

    print("[deploy_flow] deployment publicado com sucesso")


def main() -> int:
    """
    Detecta pipelines alterados e publica deployments no Prefect.

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

    # Se houve mudança em código compartilhado, republica todos os pipelines.
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

    for pipeline_dir in pipeline_dirs:
        deploy_flow(pipeline_dir=pipeline_dir, env=env)

    return 0


if __name__ == "__main__":
    sys.exit(main())
