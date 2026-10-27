# T-D30 — Build workflow (image + cosign)

- **Phase**: 3 — Deployment pipeline
- **Sequential**: first task of Phase 3
- **Depends on**: T-D10 (Dockerfile)
- **Blocks**: T-D31
- **References**: ADR-0035 §2

## Deliverables

`.github/workflows/build.yml`:

```yaml
name: build
on:
  push:
    branches: [main]
    tags: ['v*.*.*']
  workflow_dispatch:

permissions:
  contents: read
  packages: write
  id-token: write        # for cosign keyless

concurrency:
  group: build-${{ github.ref }}
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Compute tags
        id: tags
        run: |
          SHORT=${GITHUB_SHA::7}
          echo "short=$SHORT" >> $GITHUB_OUTPUT
      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ghcr.io/${{ github.repository_owner }}/budget-planner
          tags: |
            type=raw,value=sha-${{ steps.tags.outputs.short }}
            type=raw,value=main,enable={{is_default_branch}}
            type=semver,pattern={{version}}
      - uses: docker/build-push-action@v6
        id: build
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - uses: sigstore/cosign-installer@v3
      - name: Sign image
        env:
          COSIGN_YES: "true"
        run: |
          for tag in ${{ steps.meta.outputs.tags }}; do
            cosign sign --yes "${tag}@${{ steps.build.outputs.digest }}"
          done
```

## Acceptance criteria

- Push to `main` publishes `ghcr.io/<owner>/budget-planner:sha-<short>` + `:main`.
- Tag push `v0.2.0` additionally publishes `:v0.2.0`.
- `cosign verify` succeeds against every pushed tag using the GitHub OIDC issuer.

## Validation hook

```sh
cosign verify \
  --certificate-identity-regexp "^https://github.com/<owner>/budget-planner/" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  ghcr.io/<owner>/budget-planner:sha-<short>
```
