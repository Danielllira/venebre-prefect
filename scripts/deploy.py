# Refs:Deploy multiple flows: https://docs.prefect.io/v3/deploy/infrastructure-concepts/deploy-via-python/#deploy-multiple-flows
import importlib
import os
import sys
from pathlib import Path
from prefect import deploy

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ENV = os.environ.get("ENV", "stg")
WORK_POOL = os.environ.get("PREFECT_WORK_POOL")
WORKER_IMAGE = os.environ.get("WORKER_IMAGE")

IS_PROD = ENV == "prod"

changed_folders = sys.argv[1:]

def main():
    if not changed_folders:
        print("(info) No folders provided. Nothing to deploy.")
        sys.exit(0)

    if not WORK_POOL or not WORKER_IMAGE:
        print("(error) Missing PREFECT_WORK_POOL or WORKER_IMAGE env variables.")
        sys.exit(1)

    print(f"\n> Target env: {ENV} | Pool: {WORK_POOL} | Image: {WORKER_IMAGE}\n")

    deployments_to_apply = []

    for folder in changed_folders:
        folder_path = Path(folder).resolve()
        
        try:
            relative_parts = folder_path.relative_to(PROJECT_ROOT).parts
            module_name = ".".join(relative_parts) + ".flows"
        except ValueError:
            print(f"(warn) Skipping {folder}: Not inside project root.")
            continue

        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            print(f"(warn) Skipping {folder}: flows.py not found.")
            continue

        contracts = getattr(module, "pipelines", [])
        if not contracts:
            print(f"(warn) Skipping {folder}: 'pipelines' contract is missing or empty.")
            continue

        print(f"[(flow) Processing {folder}...")

        for contract in contracts:
            flow_obj = contract["flow"]
            base_tags = contract.get("tags", [])
            base_schedule = contract.get("schedule")

            # Ref: https://docs.prefect.io/v3/api-ref/prefect/flows/#prefect.flows.Flow.to_deployment
            deploy_name = flow_obj.name if IS_PROD else f"{flow_obj.name} (dev)"
            final_tags = base_tags + [ENV]
            final_schedule = base_schedule if IS_PROD else None

            deployment = flow_obj.to_deployment(
                name=deploy_name,
                tags=final_tags,
                schedules=[final_schedule] if final_schedule else [],
                work_pool_name=WORK_POOL,
            )
            deployments_to_apply.append(deployment)
            print(f" -> Prepared: {deploy_name}")

    if deployments_to_apply:
        print(f"\n[deploy] Pushing {len(deployments_to_apply)} deployments to Prefect...")
        deploy(
            *deployments_to_apply,
            image=WORKER_IMAGE,
            build=False,
            push=False,
        )
        print("(deploy) Success!")
    else:
        print("\n(info) No valid contracts found to deploy.")

if __name__ == "__main__":
    main()