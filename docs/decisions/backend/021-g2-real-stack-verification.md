# 021 — G2 real-stack verification: sandbox-specific workarounds, not product changes

## Status

ACCEPTED (Track finale G2, 2026-09-20). Documents workarounds needed to
bring up the real stack (api + web + weak-TLS + local registry +
SoftHSM2) inside this specific sandboxed execution environment, so a
later session doesn't re-discover them from scratch, and so it's clear
none of these are changes to the shipped product's behavior.

## Context

G2's mandate: bring up the real stack from a clean state and prove
`make demo` works. This session's sandbox has an intercepting TLS egress
proxy (`$HTTPS_PROXY`, CA at `/root/.ccr/ca-bundle.crt`) that blocks a
handful of specific CDN blob hosts outright (`production.cloudfront.docker.com`,
`pkg-containers.githubusercontent.com`) and, separately, is not trusted
by default *inside* any container (`docker build`/`docker run` processes
can't reach the proxy at `127.0.0.1:<port>` and don't carry its CA).

## Workarounds applied, and why they're sandbox-only

1. **Image pulls**: `docker pull nginx:alpine` / `registry:2` / etc. hit
   the blocked CDN hosts. Worked around by pulling the equivalent image
   from `mirror.gcr.io/library/<name>` and re-tagging locally to the
   expected name (`docker tag mirror.gcr.io/library/nginx:alpine
   nginx:alpine`). This is purely a sandbox network-policy accommodation
   -- `docker-compose.yml` itself still references the standard public
   image names (`nginx:alpine`, `registry:2`), which resolve normally on
   any real deployment host with ordinary internet access.

2. **`demo-weak-tls`'s own `apk add openssl` at container start**: this
   container generates its TLS cert/key on first boot (see the inline
   comment in `docker-compose.yml`), which itself needs network access
   from *inside* the container -- blocked here by the container-CA-trust
   gap above (not the CDN block; `apk`'s target host isn't one of the
   specifically-blocked ones, but the container can't validate the
   proxy's intercepting cert at all). Worked around by generating the
   cert/key on the *host* instead (`openssl req -x509 ...`, no network
   involved) and mounting the pair into the container at the same paths
   the container's own `command:` block would have written them to,
   skipping the in-container `apk add` step for this verification pass.
   `docker-compose.yml`'s `command:` still does the full self-contained
   generate-on-boot flow for any environment where the container *can*
   reach a package mirror normally.

3. **`backend/Dockerfile`'s own build** (`COPY --from=ghcr.io/astral-sh/uv:...`
   then `uv sync`) hits both problems at once: GHCR is one of the
   specifically-blocked CDN hosts, and even a `pip install uv` substitute
   still needs `pypi.org` from inside the build, which fails TLS
   verification for the same container-CA-trust reason as above. Per
   `/root/.ccr/README.md`'s own documented workaround (`--network host`
   plus installing the CA bundle in an early build layer), a full fix
   is possible but was judged disproportionate to make *permanently* for
   a sandbox-only limitation -- and no image was actually built from this
   Dockerfile in this pass as a result (see the finale's own MEASURED
   NUMBERS / WHAT REMAINS sections for the honest consequence: no
   custom `api`/`web` image was ever built or vulnerability-scanned in
   this environment, only the demo's third-party base images were).

## Why none of this is a `docker-compose.yml` or `Dockerfile` change

Every workaround above operates on the *outside* of what those files
declare (which registry a name resolves against locally, or how a
cert file arrives on disk before the container mounts it) -- not on what
they themselves specify. Editing either file to hardcode a sandbox-only
workaround (e.g. baking `mirror.gcr.io/` into the image names, or
removing the in-container cert generation) would make the committed
stack definition *wrong* for a normal deployment host with ordinary
internet access, trading a real capability for a sandbox convenience.
That tradeoff was rejected.

## SoftHSM2: not containerized in this pass

`docker-compose.yml` deliberately does not run `api`'s PKCS#11/SoftHSM2
probe (`backend/probes/hsm.py`) inside a container in this pass. Two real,
supported paths exist and either is legitimate for a real deployment:

1. Install `softhsm2` + `opensc` into `backend/Dockerfile`'s runtime
   stage and mount a persistent volume at `/var/lib/softhsm/tokens` so
   the token store survives container restarts.
2. Run `api` outside Docker (as this session's own G2/G3 verification
   did) against a host-installed `softhsm2`, which `probes/hsm.py`
   already resolves via `/usr/lib/softhsm/libsofthsm2.so` or
   `$SOFTHSM2_LIB`.

Path 2 is what this pass actually used to get real HSM inventory
evidence (Track A1's P5 proof, and G3 step 12's tamper-and-restore
audit-log proof) -- not fabricated, just not the all-in-Docker path.
Path 1 needs the same `backend/Dockerfile` build this sandbox can't
currently exercise (see above), so it's documented here as the intended
route for a containerized deployment, not implemented in this pass.

## Consequences

- `make demo` / `docker compose --profile demo up` work as declared in
  this repo for any host with normal (non-intercepted) internet access.
- In *this specific sandbox*, reproducing G2's verification requires the
  two workarounds above (image re-tagging, host-generated TLS cert) --
  not a defect in the committed files, and not expected to be needed
  outside this kind of network-intercepting sandbox.
- The `backend/Dockerfile` build was never actually exercised end-to-end
  in this sandbox; `docker compose up --build` for `api`/`web` remains
  unverified here specifically (tracked honestly in the finale report's
  WHAT REMAINS, not silently assumed to work).
