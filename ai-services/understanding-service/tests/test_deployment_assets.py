from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]


def test_dockerfile_packages_service_with_ffmpeg_and_non_root_user():
    dockerfile = (SERVICE_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "python:3.12-slim" in dockerfile
    assert "ffmpeg" in dockerfile
    assert "USER appuser" in dockerfile
    assert "python -m scripts.docker_entrypoint" in dockerfile


def test_compose_file_runs_mysql_and_analysis_with_env_file_shape():
    compose = (SERVICE_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "mysql:" in compose
    assert "understanding-service:" in compose
    assert "MYSQL_HOST: mysql" in compose
    assert "ZHIPUAI_API_KEY" in compose
    assert "DEEPSEEK_API_KEY" in compose
    assert "./outputs:/app/outputs" in compose
    assert "./input:/input:ro" in compose


def test_k8s_manifest_uses_config_map_secret_and_persistent_outputs():
    manifest_dir = REPO_ROOT / "deploy" / "k8s" / "understanding-service"
    manifest = "\n---\n".join(
        path.read_text(encoding="utf-8") for path in sorted(manifest_dir.glob("*.yaml"))
    )
    analysis_job = (manifest_dir / "analysis-job.yaml").read_text(encoding="utf-8")

    assert "kind: ConfigMap" in manifest
    assert "kind: Secret" in manifest
    assert "kind: Job" in manifest
    assert "secretKeyRef" in manifest
    assert "ZHIPUAI_API_KEY" in manifest
    assert "DEEPSEEK_API_KEY" in manifest
    assert "mountPath: /app/outputs" in manifest
    assert "\n---\napiVersion: v1\nkind: PersistentVolumeClaim" in analysis_job
    assert "kind: Secret" not in analysis_job


def test_env_example_has_placeholders_without_real_keys():
    env_example = (SERVICE_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "ZHIPUAI_API_KEY=" in env_example
    assert "DEEPSEEK_API_KEY=" in env_example
    assert "MYSQL_PASSWORD=" in env_example
    assert "your_" in env_example
    assert "sk-" not in env_example
