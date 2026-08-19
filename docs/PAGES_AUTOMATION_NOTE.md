# GitHub Pages Automation Note

The Dashboard GitHub Pages workflow is designed to deploy automatically from `main` once GitHub Pages is enabled for the repository.

GitHub's standard `GITHUB_TOKEN` cannot perform first-time Pages enablement through `actions/configure-pages` `enablement: true`; that path requires an additional token / GitHub App with the documented Pages and administration permissions.

After the one-time repository Pages enablement, the workflow uses the official sequence:

1. `actions/configure-pages@v5`
2. `actions/upload-pages-artifact@v4`
3. `actions/deploy-pages@v4`

The dashboard remains PAPER-ONLY and does not expose live-trading execution.
