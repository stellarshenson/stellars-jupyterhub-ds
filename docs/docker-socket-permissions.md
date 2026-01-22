# Docker Access Control

Group-based Docker access for user containers via two built-in groups.

| Group | Effect |
|-------|--------|
| `docker-sock` | Mounts `/var/run/docker.sock` |
| `docker-privileged` | Runs container with `--privileged` flag |

**Implementation** (`config/jupyterhub_config.py`):
```python
BUILTIN_GROUPS = ['docker-sock', 'docker-privileged']

async def pre_spawn_hook(spawner):
    if 'docker-sock' in user_groups:
        spawner.volumes['/var/run/docker.sock'] = '/var/run/docker.sock'
    if 'docker-privileged' in user_groups:
        spawner.extra_host_config['privileged'] = True
```

**Management**: Admin panel `/hub/admin` -> Groups. User must restart server after membership change.

**Security**: Both groups grant significant privileges. Only grant to trusted users.
