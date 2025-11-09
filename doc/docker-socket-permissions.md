# Docker Socket Access Control

Group-based docker.sock access for user containers. Controlled via `docker-privileged` built-in group.

**Implementation** (`config/jupyterhub_config.py`):
```python
async def pre_spawn_hook(spawner):
    if any(group.name == 'docker-privileged' for group in spawner.user.groups):
        spawner.volumes['/var/run/docker.sock'] = '/var/run/docker.sock'
```

**Built-in Group**:
- `BUILTIN_GROUPS = ['docker-privileged']` in config
- Auto-recreates if deleted (startup script + pre-spawn hook)
- Managed via admin panel at `/hub/admin` -> Groups
- User must restart server after membership change

**Security**: Docker socket = root-equivalent Docker host access. Only grant to trusted users.
