# Security Policy

## Supported versions

Only the latest release receives security fixes. Fixes are published for the
current major version; upgrade before reporting against an older one.

| Version | Supported |
| --- | --- |
| 1.1.x | yes |
| < 1.1 | no |

## Reporting a vulnerability

**Do not open a public issue.** Use GitHub's private reporting:

[**Report a vulnerability**](https://github.com/serkanalgur/dragonflydb-panel/security/advisories/new)

Please include:

- what the vulnerability allows an attacker to do
- steps to reproduce, ideally a minimal `curl` or `redis-cli` invocation
- the plugin version, aaPanel version, and the panel OS
- whether the attacker needs panel access, or only network access to the
  DragonflyDB port

Expect an acknowledgement within 72 hours and an assessment within seven days.
If a fix is warranted, I will agree a disclosure date with you before publishing.

## Scope

This project is an aaPanel plugin. It runs as the panel's own user and manages
a local Docker container.

**In scope**

- Anything reachable through the plugin's HTTP endpoints that should not be
- Command injection via a plugin argument reaching a shell
- Credentials written to disk with insufficient permissions
- The uninstaller leaving containers, volumes, or data behind
- The plugin escaping the boundaries of its own settings and deployment

**Out of scope**

- Vulnerabilities in aaPanel itself — report those to the aaPanel maintainers
- Vulnerabilities in DragonflyDB itself — report those to the DragonflyDB
  project
- Vulnerabilities in Docker or Compose
- A DragonflyDB instance exposed beyond the running server with no password
  configured, which is a configuration choice, not a defect

## Deployment notes

The plugin defaults to binding `127.0.0.1` on port `6380` and sets no password.
Before binding to `0.0.0.0`:

- set a password in the plugin settings
- restrict access at the firewall
- remember that `network_mode: host` means the container has no network
  namespace isolation

`settings.json`, which may contain a password, is written with mode `0600`.
