# OpenClaw local smoke test

This directory is an isolated, migration-friendly OpenClaw Gateway test. It does
not change the existing FastAPI, frontend, PostgreSQL, or tax calculators.

## Security boundary used for the smoke test

- Official Docker Hub image, pinned by digest.
- Gateway listens on the container network interface, but is published only on
  the host's `127.0.0.1:18789` (Docker needs this split; container loopback is
  not reachable through a port mapping).
- Token authentication is required.
- The OpenAI-compatible chat endpoint, image input limits, and web-search switch
  are enabled, but a model/search credential is intentionally blank in
  `.env.example` until the operator supplies one.
- Dangerous host/control-plane tools are denied in the persisted config. The
  AutoPolicy business tools are executed by the FastAPI proxy, not by arbitrary
  OpenClaw shell/file tools.
- The container drops Linux capabilities, enables `no-new-privileges`, and uses a
  read-only root filesystem. Only `state/` and `workspace/` are writable.

## Start on Windows PowerShell

```powershell
Copy-Item .env.example .env
# Edit .env and set a long random OPENCLAW_GATEWAY_TOKEN.
# Add OPENAI_API_KEY (or the reviewed provider setup) and BRAVE_API_KEY when ready.
docker compose up -d
docker compose ps
docker compose logs --tail 100 gateway
docker compose exec gateway node openclaw.mjs gateway health --url ws://127.0.0.1:18789 --token $env:OPENCLAW_GATEWAY_TOKEN
```

The UI/WebSocket endpoint is local-only at `http://127.0.0.1:18789/`. The
AutoPolicy browser must not call this port; set the backend's `GAIS_OPENCLAW_*`
variables so FastAPI proxies model requests on port 8000.

## Stop without deleting data

```powershell
docker compose down
```

Do not use `docker compose down -v` for this test: the `state/` directory is the
portable OpenClaw configuration/session store.

## Server migration

Copy this directory (including `state/` and `workspace/`) to the server, install
Docker Engine/Compose, create a new `.env` with a server-only token, then run
`docker compose up -d`. Keep the image digest unchanged for reproducibility.

On Linux, make the bind-mounted directories writable by the image's `node` user
before starting (the official image uses UID 1000):

```bash
sudo chown -R 1000:1000 state workspace
```

Before production use, replace the smoke-test `--dev` command with a reviewed
production config, connect the existing backend through a server-side proxy, and
add explicit allowlisted tools. Never expose port 18789 directly to the public
internet.
