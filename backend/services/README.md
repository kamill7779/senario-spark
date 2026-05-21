# Go Services

Each service should own its own `cmd` entrypoint and `internal` package tree.

Keep cross-service contracts in `contracts/` rather than importing another service's internal code.

