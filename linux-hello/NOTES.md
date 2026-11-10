# Linux-Hello packaging notes

Unofficial Fedora packaging for
[`kennycoder/linux-hello`](https://github.com/kennycoder/linux-hello).
Upstream does not publish a Fedora package, so this repository carries the
RPM spec and the SELinux integration.

## Why the extra packaging

The upstream tarball is source only. The spec adds what a Fedora package needs:

- Builds the Rust workspace, the C++/OpenCV bridge, and the KDE KCM.
- Installs the daemon, CLI, GUI, PAM module, polkit action, models, icons,
  desktop files, and systemd unit.
- Integrates the PAM module with authselect or pam-auth-update.
- Declares runtime dependencies and handles service scriptlets.
- Carries the model license split: code and SFace are Apache-2.0, YuNet is MIT.

Without these pieces the upstream source builds but does not behave as an
installed Fedora system service.

## Why the SELinux policy

Fedora runs SELinux in enforcing mode. Plasma Login Manager’s PAM helper runs
as `xdm_t`, while `linux-hellod` creates `/run/linux-hello.sock` with the
generic `var_run_t` type. SELinux denies the login helper access:

```text
avc: denied { getattr } ... scontext=...:xdm_t ... tcontext=...:var_run_t ... tclass=sock_file
```

The PAM module then returns `PAM_IGNORE`, and login silently falls back to the
password prompt. Sudo and the lock screen work because they run as
`unconfined_t`.

The package therefore ships a `linux-hello-selinux` subpackage:

- Defines a dedicated `linux_hello_var_run_t` type.
- Maps only `/run/linux-hello.sock` to that type.
- Allows `xdm_t` to access that type, not every `var_run_t` socket.
- Loads the module in `%post` and removes it in `%postun`.
- Pulls the subpackage only when `selinux-policy-targeted` is installed.

## Why the relabel helper

Upstream creates the socket as `var_run_t`; changing that would require an
upstream patch. The package installs a systemd drop-in and a small helper
that waits for the socket after service start and runs:

```sh
restorecon /run/linux-hello.sock
```

That relabels the socket to `linux_hello_var_run_t` after each service start,
so the dedicated policy applies without an upstream change.

## Caveats

- The relabel step is a race workaround. The helper waits up to 60 seconds for
  the socket; increase the loop count if the daemon takes longer.
- If the daemon ever recreates the socket without a service restart, the label
  is lost until the next restart. The current daemon creates it at startup.
- The systemd drop-in is package-owned under `/usr/lib/systemd/system/`; local
  edits there will be overwritten.
- The policy source is GPL-2.0-or-later, while the main package is
  Apache-2.0 AND MIT.
- Passwordless login does not unlock KWallet or GNOME Keyring: face auth
  returns success without a password token, so the wallet prompts later.
