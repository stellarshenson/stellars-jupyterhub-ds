# Docker Socket Access Control

Group-based Docker socket access for user containers enabling container orchestration from within JupyterLab. Controlled via `docker-privileged` built-in group.

**Key Implementation Facts**:
- JupyterHub container mounts `/var/run/docker.sock:rw` for DockerSpawner (required)
- User containers conditionally receive socket based on group membership
- Pre-spawn hook checks `user.groups` before mounting socket
- Group membership changes require server restart to take effect
- Built-in group protected from deletion (auto-recreates)

**Pre-Spawn Hook** (`config/jupyterhub_config.py`):
```python
async def pre_spawn_hook(spawner):
    user = spawner.user

    # Check if user is in docker-privileged group
    if any(group.name == 'docker-privileged' for group in user.groups):
        spawner.extra_host_config = {
            'binds': {
                '/var/run/docker.sock': {
                    'bind': '/var/run/docker.sock',
                    'mode': 'rw'
                }
            }
        }
```

**Built-in Group System**:
- Single source of truth: `BUILTIN_GROUPS = ['docker-privileged']` in `jupyterhub_config.py`
- Startup script `02_ensure_groups.py` reads config and creates missing groups
- Pre-spawn hook recreates group if deleted during runtime
- Cannot be permanently removed

**Managing Access** (via admin panel at `/hub/admin`):
1. Navigate to Groups section
2. Click `docker-privileged` group
3. Add/remove usernames
4. User must restart server for changes to apply

**Security Implications**:
Docker socket provides root-equivalent host access:
- Create privileged containers
- Mount any host directory
- Access other users' containers/volumes
- Read sensitive host files
- Escape container isolation

Only grant access to fully trusted users who already have legitimate root/sudo equivalency.

**Use Cases**:
- Building Docker images within JupyterLab
- Running development services (databases, APIs)
- Container orchestration development
- Infrastructure as Code testing
- Teaching Docker concepts

**Auditing**:
```bash
# View Docker daemon logs
sudo journalctl -u docker.service -f

# Monitor Docker events
docker events
```
