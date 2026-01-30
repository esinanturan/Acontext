# Acontext Roadmap

current version: v0.0

## Integrations

We're always welcome to integrations PRs:

- If your integrations involve SDK or cli changes, pull requests in this repo.
- If your integrations are combining Acontext SDK and other frameworks, pull requests to https://github.com/memodb-io/Acontext-Examples where your templates can be downloaded through `acontext-cli`: `acontext create my-proj --template-path "LANGUAGE/YOUR-TEMPLATE"`



## Long-term effort
- Increase robustness; Reduce latency
- Safer storage

## v0.1

Disk - more agentic interface

- [ ] Disk: file/dir sharing UI Component.

Session - Context Engineering

- [ ] Session - Context Offloading based on Disks
- [ ] Session Message labeling (e.g., like, dislike, feedback)
- [ ] Session search: support session search by embedding similarity.

Session - Metadata

- [ ] Session metadata: add metadata field (JSONB) and support filter

Observability

- [ ] User telemetry observation, service chain observation
- [ ] Improve internal service observation content

Dashboard

- [ ] Observability dashboard: display user telemetry metrics and service chain traces
- [ ] Internal service observation UI: visualize service health, latency, and error rates
- [ ] Session Message labeling UI: interface for like/dislike/feedback actions
- [ ] Disk operation observability: track file/dir sharing and artifact access metrics
- [ ] Sandbox resource monitoring UI: display sandbox usage and performance metrics

Sandbox

- [x] Add sandbox resource in Acontext
- [x] Integrate Claude Skill 

Sercurity&Privacy

- [ ] Use project api key to encrypt context data in S3

Integration

- [ ] Claude Agent SDK
- [ ] OpenCode

LLM Integrations

- [ ] Add litellm as the proxy
