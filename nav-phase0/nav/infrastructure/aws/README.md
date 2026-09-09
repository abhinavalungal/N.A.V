# AWS deployment (target shape, not yet provisioned)

Nothing here is deployed, and nothing in the codebase reads an AWS setting -
there is no S3 bucket, no region, no credentials to supply. This records the
intended topology so Phase 10 has a starting point rather than a blank page.
For a prototype, Render (see `docs/deployment.md`) or plain `docker compose`
is the shorter path.

    Internet
       |
    Application Load Balancer
       |
       +-- web  (Next.js standalone, EC2 or ECS service)
       |
       +-- api  (FastAPI, EC2 or ECS service)
              |
              +-- RDS PostgreSQL 16 + pgvector   (private subnet)
              +-- ElastiCache Redis              (private subnet)
              +-- S3                             (documents, run snapshots)

    worker (Celery) runs as its own service against the same Redis and RDS.

Notes carried forward from the architecture:

- Workers scale separately from the API; optimisation load must never affect
  request latency.
- Secrets come from SSM Parameter Store or Secrets Manager, injected as
  environment variables. The application already reads everything from the
  environment.
- Logs are structured JSON on stdout, which CloudWatch ingests without a
  parser.
- `/health` is the ALB target-group check; `/ready` gates deployment cutover.
