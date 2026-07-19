# Release GitHub App

Releases use a GitHub App installation token instead of a personal access
token. The App token is short-lived and lets Python Semantic Release commit the
version and changelog, push the release tag, and create the GitHub release.

## Organization setup

1. Create a GitHub App owned by the `Python-roborock` organization.
2. Disable webhooks and grant the App **Contents: Read and write** repository
   permission. No other optional repository or organization permissions are
   required.
3. Install the App only on the `python-roborock` repository.
4. In the `main` branch protection settings, add the App to **Allow specified
   actors to bypass required pull requests**. Without this bypass,
   semantic-release cannot commit the generated release files back to `main`.
5. Add the App's client ID as the repository variable
   `RELEASE_APP_CLIENT_ID`.
6. Generate a private key for the App and save the complete PEM file as the
   `release` environment secret `RELEASE_APP_PRIVATE_KEY`.

After a successful release using the App, remove the old maintainer-owned
`GH_TOKEN` repository secret.
