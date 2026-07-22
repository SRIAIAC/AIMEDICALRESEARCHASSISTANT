# Deployment

The app is live at **http://34.44.85.232/** — a Google Cloud Compute Engine
VM running the full stack via `docker-compose.prod.yml`.

## What's running

| Resource | Value |
|---|---|
| GCP project | `ai-medresearch-7569` (isolated from any other project on this account) |
| VM | `medresearch-vm`, zone `us-central1-a`, `e2-standard-2` (2 vCPU / 8GB RAM), 50GB disk |
| Static IP | `34.44.85.232` (reserved — survives VM restarts) |
| Firewall | `allow-http-https` (80/443, tag `web`) + GCP's default SSH rule |
| Containers | `ollama`, `backend` (FastAPI), `frontend` (nginx serving the React build), `caddy` (reverse proxy on 80/443) |

Caddy path-routes `/api/*` to the backend and everything else to the
frontend, so the browser only ever talks to one origin — no CORS involved
in normal use. Ollama runs as its own container with a persistent volume
(`ollama_models`) holding the pulled `llama3.2` and `nomic-embed-text`
weights, so they aren't re-downloaded on restart. Postgres is **not**
deployed — the app doesn't use it yet (`db/session.py` is unwired; see
ARCHITECTURE.md §16).

## Redeploying after a code change

From your machine, in the project root:

```bash
tar -czf /tmp/medresearch-deploy.tar.gz \
  --exclude='venv' --exclude='node_modules' --exclude='frontend/dist' \
  --exclude='backend/data' --exclude='__pycache__' --exclude='.pytest_cache' \
  backend frontend Caddyfile docker-compose.prod.yml

gcloud compute scp /tmp/medresearch-deploy.tar.gz medresearch-vm:medresearch-deploy.tar.gz \
  --project=ai-medresearch-7569 --zone=us-central1-a

gcloud compute ssh medresearch-vm --project=ai-medresearch-7569 --zone=us-central1-a --command="
  rm -rf ~/medresearch-new && mkdir ~/medresearch-new &&
  tar -xzf ~/medresearch-deploy.tar.gz -C ~/medresearch-new &&
  cp ~/medresearch/backend/.env.prod ~/medresearch-new/backend/.env.prod &&
  rm -rf ~/medresearch && mv ~/medresearch-new ~/medresearch &&
  cd ~/medresearch && sudo docker compose -f docker-compose.prod.yml up -d --build
"
```

`.env.prod` (with its generated `JWT_SECRET_KEY`) lives only on the VM and
in your local `backend/.env.prod` — it's gitignored and isn't part of the
tarball's source tree, so the command above explicitly copies the existing
one across rather than overwriting it with the (secret-less) example.

## Adding a real domain (optional — gets you free HTTPS)

1. Point an A record for your domain at `34.44.85.232`.
2. SSH in and set `SITE_ADDRESS`, then recreate Caddy:
   ```bash
   gcloud compute ssh medresearch-vm --project=ai-medresearch-7569 --zone=us-central1-a --command="
     cd ~/medresearch &&
     echo 'SITE_ADDRESS=yourdomain.com' > .env &&
     sudo docker compose -f docker-compose.prod.yml up -d caddy
   "
   ```
Caddy auto-detects the change and gets a Let's Encrypt cert with no other
config. Update `backend/.env.prod`'s `CORS_ORIGINS` to the new domain too
(cosmetic — same-origin requests via Caddy don't actually need it, but
direct API access would).

## Checking on it / logs

```bash
gcloud compute ssh medresearch-vm --project=ai-medresearch-7569 --zone=us-central1-a --command="sudo docker compose -f ~/medresearch/docker-compose.prod.yml ps"
gcloud compute ssh medresearch-vm --project=ai-medresearch-7569 --zone=us-central1-a --command="sudo docker compose -f ~/medresearch/docker-compose.prod.yml logs backend --tail 50"
```

## Cost / stopping it

`e2-standard-2` runs ~$50/mo on-demand while the VM exists and is running,
billed by the minute — there's no free tier here. To stop billing for
compute (keeps the disk, IP, and everything configured — just not running):

```bash
gcloud compute instances stop medresearch-vm --project=ai-medresearch-7569 --zone=us-central1-a
```

Restart it later with `gcloud compute instances start ...` — the static IP
and Docker setup persist; `docker compose` has restart policies
(`unless-stopped`) so the stack comes back up automatically once the VM
boots. To tear everything down completely (VM, disk, IP, and stop the
reserved-IP charge too):

```bash
gcloud compute instances delete medresearch-vm --project=ai-medresearch-7569 --zone=us-central1-a
gcloud compute addresses delete medresearch-ip --project=ai-medresearch-7569 --region=us-central1
```

Or delete the whole project (`gcloud projects delete ai-medresearch-7569`)
to remove every resource associated with this deployment at once.

## Local Docker (dev, not this cloud setup)

`docker-compose.yml` (no `-prod` suffix) is the separate, unrelated local
dev flow — it expects `ollama serve` running on your own machine via
`host.docker.internal` rather than an in-cluster Ollama container, and
serves the frontend with `vite preview` instead of nginx. Don't mix the
two compose files.
