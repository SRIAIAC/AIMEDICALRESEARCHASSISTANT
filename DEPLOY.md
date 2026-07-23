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
| Containers | `postgres`, `ollama`, `backend` (FastAPI), `frontend` (nginx serving the React build), `caddy` (reverse proxy on 80/443) |

Caddy path-routes `/api/*` to the backend and everything else to the
frontend, so the browser only ever talks to one origin — no CORS involved
in normal use. Ollama runs as its own container with a persistent volume
(`ollama_models`) holding the pulled `llama3.2` and `nomic-embed-text`
weights, so they aren't re-downloaded on restart. Postgres persists
research reports (`/api/v1/research`'s history) in a `postgres_data`
volume; the backend container runs `alembic upgrade head` on startup, so
the schema is created/updated automatically — no manual migration step on
this VM. Every other agent endpoint is still request/response only, no
persistence (see ARCHITECTURE.md §16).

## Continuous deployment (GitHub Actions)

Every push to `main` runs `.github/workflows/ci.yml`: backend tests +
frontend build, then (only if both pass) a `deploy` job that packages and
redeploys this same VM — the automated version of the manual steps below.
The deploy job sits behind a `production` GitHub Environment, so it pauses
for a manual approval click in the Actions UI before it touches anything;
CI on pull requests never reaches this job (`if: github.ref == 'refs/heads/main'`).

One-time setup (do this once, from a machine with `gcloud` already
authenticated to the `ai-medresearch-7569` project):

1. **Create a deploy-only service account** and grant it just enough to
   push files and run `docker compose` over SSH — no broader project access:
   ```bash
   gcloud iam service-accounts create gh-actions-deploy \
     --project=ai-medresearch-7569 --display-name="GitHub Actions deploy"

   gcloud projects add-iam-policy-binding ai-medresearch-7569 \
     --member="serviceAccount:gh-actions-deploy@ai-medresearch-7569.iam.gserviceaccount.com" \
     --role="roles/compute.instanceAdmin.v1"

   gcloud projects add-iam-policy-binding ai-medresearch-7569 \
     --member="serviceAccount:gh-actions-deploy@ai-medresearch-7569.iam.gserviceaccount.com" \
     --role="roles/iam.serviceAccountUser"
   ```
   (`compute.instanceAdmin.v1` is what lets `gcloud compute ssh`/`scp` push
   an ephemeral SSH key to the VM's metadata and connect — the same
   mechanism the manual flow below relies on.)

2. **Create and download a key** for that service account:
   ```bash
   gcloud iam service-accounts keys create gh-actions-deploy-key.json \
     --iam-account=gh-actions-deploy@ai-medresearch-7569.iam.gserviceaccount.com
   ```
   Treat this file like a password — it's a standing credential. Delete it
   locally once it's in GitHub (step 3), and rotate it
   (`gcloud iam service-accounts keys create/delete`) if it's ever exposed.

3. **Add it as a repo secret**: GitHub repo → Settings → Secrets and
   variables → Actions → New repository secret → name it `GCP_SA_KEY`,
   paste the entire contents of `gh-actions-deploy-key.json` as the value.

4. **Create the `production` environment**: Settings → Environments → New
   environment → name it exactly `production` → add yourself (or whoever
   should approve prod deploys) under "Required reviewers". Without this,
   referencing `environment: production` in the workflow still works, but
   with no protection rule the job runs immediately on every push to main —
   the reviewer step is what makes deploys pause for approval.

After that, deploying is just: merge to `main`, wait for the `backend` and
`frontend` checks, then approve the `deploy` job when GitHub prompts.

## Redeploying manually (fallback / for local testing)

The steps CI automates above, if you'd rather run them yourself — e.g. to
test a change before it's on `main`, or if Actions is down. From your
machine, in the project root:

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
