# rpm-packages

Fedora RPM packaging for several upstream projects, published through Copr.

This is a packaging-only repository. It does not fork or modify upstream
projects; each package builds from upstream releases.

Each package lives in its own directory with a spec and any local sources it
needs, such as patches or SELinux policy. Shared automation at the repository
root handles Copr SRPM builds and scheduled upstream release checks.

Package-specific rationale and caveats are documented in each package’s
`NOTES.md`.

Current packages:

| Package | Upstream |
|---|---|
| `linux-hello` | [`kennycoder/linux-hello`](https://github.com/kennycoder/linux-hello) |
