# Understanding Service on Kubernetes

Build and publish the image first:

```powershell
cd D:\Project\senario-spark\.worktrees\analysis-pipeline-mysql\ai-services\understanding-service
docker build -t senariospark/understanding-service:local .
```

For a real cluster, replace the image tag in `analysis-job.yaml` with the pushed registry tag.

Quick secret configuration:

```powershell
kubectl create secret generic understanding-service-secrets `
  --from-literal=MYSQL_PASSWORD="<mysql-password>" `
  --from-literal=ZHIPUAI_API_KEY="<zhipuai-key>" `
  --from-literal=DEEPSEEK_API_KEY="<deepseek-key>" `
  --dry-run=client -o yaml | kubectl apply -f -
```

Set `EPISODE_ID`, `VIDEO_INPUT`, and MySQL connection values in the ConfigMap section, then run:

```powershell
kubectl apply -f D:\Project\senario-spark\.worktrees\analysis-pipeline-mysql\deploy\k8s\understanding-service\analysis-job.yaml
kubectl logs job/understanding-service-analysis -f
```

`secret.example.yaml` is only a template. Do not apply it with placeholder values over a real
cluster Secret.
