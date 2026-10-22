# Security

blastbench deliberately runs misbehaving agents, so the sandbox boundary matters. If you discover a way for a process inside the `sandbox` container to reach the network, the host, the runner's API key or the exec-server token, please open a private security advisory on this repository (Security tab, "Report a vulnerability") rather than a public issue.

Out of scope: container-escape bugs in Docker or the Linux kernel themselves. Never run this with `--privileged`, a mounted Docker socket or host networking.
