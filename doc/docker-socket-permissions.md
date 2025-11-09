# Docker Socket Permissions and Access Control

The JupyterHub platform requires Docker socket access for spawning and managing user containers. Additionally, trusted users can be granted Docker socket access within their JupyterLab environments for container orchestration tasks.

**Security Context:**
- Docker socket (`/var/run/docker.sock`) provides root-equivalent access to the host system
- Any process with socket access can create privileged containers, mount host directories, and execute commands as root
- JupyterHub container requires socket access for DockerSpawner functionality
- User containers optionally receive socket access based on group membership
- Socket access should only be granted to fully trusted administrators and users

## JupyterHub Container Socket Access

The JupyterHub container requires read-write access to Docker socket for core functionality. The `compose.yml` file mounts the socket directly into the container:

```yaml
services:
  jupyterhub:
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:rw
```

This mount enables DockerSpawner to create user containers, manage volumes, and control container lifecycle. The JupyterHub process runs as root inside its container and has unrestricted Docker daemon access. This design is intentional - DockerSpawner needs this level of access to dynamically spawn isolated environments per user.

**What JupyterHub Does with Socket Access:**
- Creates user JupyterLab containers with `docker run` equivalent commands
- Manages user-specific Docker volumes (home, workspace, cache)
- Removes containers when users stop their servers
- Restarts user containers for server restart functionality
- Deletes volumes when users reset their storage through volume management feature

## User Container Socket Access

Users can optionally receive Docker socket access within their spawned JupyterLab containers. This enables advanced workflows like building Docker images, running additional containers for development, or deploying services from within JupyterLab.

Access is controlled through JupyterHub's built-in group system. Only users added to the `docker-privileged` group receive socket access. The group is created automatically on platform startup and protected from deletion.

**Implementation via Pre-Spawn Hook:**

The platform uses a pre-spawn hook in `jupyterhub_config.py` to conditionally mount the Docker socket:

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

This hook executes before every container spawn. Users outside the group spawn without socket access. Group membership changes require stopping and restarting the user's server to take effect.

## Managing Privileged Users

Administrators control Docker socket access through the JupyterHub admin panel at `/hub/admin`. The interface provides group management under the "Groups" section.

**Granting Socket Access:**
1. Admin logs into JupyterHub
2. Navigate to Admin Panel
3. Click "Groups" in the top menu
4. Select `docker-privileged` group
5. Add usernames to the group member list
6. Save changes

Users must restart their JupyterLab server for group membership changes to apply. The next spawn will include or exclude Docker socket based on current group membership.

**Revoking Socket Access:**
1. Remove user from `docker-privileged` group in admin panel
2. Instruct user to stop their server
3. User starts server again without socket access

## Built-in Group Protection

The `docker-privileged` group is a built-in protected group that cannot be permanently deleted. The platform defines built-in groups in `jupyterhub_config.py`:

```python
BUILTIN_GROUPS = ['docker-privileged']
```

A startup script reads this list and creates missing groups before JupyterHub launches. Additionally, the pre-spawn hook recreates the group if deleted during runtime. This ensures the security model cannot be accidentally bypassed by deleting the group.

**Adding New Built-in Groups:**

To add another protected group (e.g., for different permission levels), edit only the `BUILTIN_GROUPS` list in `jupyterhub_config.py`:

```python
BUILTIN_GROUPS = ['docker-privileged', 'gpu-access', 'shared-admin']
```

The startup script automatically handles creation without requiring changes to the script itself. This follows the DRY (Don't Repeat Yourself) principle with a single source of truth.

## Security Implications

Granting Docker socket access to user containers introduces significant security considerations. Users with socket access can effectively become root on the host system through various attack vectors.

**What Users Can Do with Socket Access:**

- Create privileged containers with `--privileged` flag
- Mount any host directory into containers including `/`, `/etc`, `/root`
- Run containers as root with full capabilities
- Access other users' container filesystems and volumes
- Read sensitive files from host (SSH keys, password files, application secrets)
- Install kernel modules or modify system configuration
- Escape container isolation entirely

This is not a vulnerability - it is the expected behavior of Docker socket access. The socket provides the same level of access as running commands as root directly on the host. Therefore, only grant access to users who already have legitimate root/sudo access or equivalent trust level.

## Use Cases for Privileged Access

Despite the security implications, Docker socket access enables powerful legitimate workflows for advanced users and administrators.

**Valid Use Cases:**
- Building custom Docker images within JupyterLab for experimentation
- Running development databases or services alongside notebooks
- Creating isolated test environments for CI/CD prototyping
- Container orchestration development and testing
- Infrastructure as Code development with Docker-based tools
- Teaching and demonstrating Docker concepts in educational settings

The platform is designed for environments where users already have high trust levels, such as internal data science teams, research labs, or development environments where users would have SSH access anyway.

## Auditing Socket Usage

Docker daemon logs all commands received through the socket. These logs appear in the host system logs and can be monitored for suspicious activity.

**Viewing Docker Daemon Logs:**
```bash
# On Ubuntu/Debian with systemd
sudo journalctl -u docker.service -f

# Or check Docker events
docker events
```

Organizations requiring strict audit trails should configure Docker daemon logging to forward to a centralized logging system. This enables security teams to detect and respond to misuse of Docker socket access.

## Alternative: Docker-in-Docker (DinD)

An alternative to mounting the host Docker socket is running Docker daemon inside user containers (Docker-in-Docker). This provides container isolation between user Docker operations and the host Docker daemon.

**DinD Tradeoffs:**
- Better isolation - user cannot access host containers or volumes
- Worse performance - additional daemon overhead per user
- Complex networking - requires privileged mode anyway for inner daemon
- Storage overhead - each user needs separate image cache
- Still requires privileged mode - security benefit is limited

This platform uses direct socket mounting for simplicity and performance. The group-based access control provides sufficient security for the target use case of trusted data science teams.

## Disabling Privileged Access

To completely disable user Docker socket access, remove the pre-spawn hook logic from `jupyterhub_config.py`:

```python
# Comment out or remove the pre_spawn_hook function entirely
# async def pre_spawn_hook(spawner):
#     ...
```

This prevents all users from receiving socket access regardless of group membership. The JupyterHub container itself still requires socket access for DockerSpawner functionality - this cannot be disabled without fundamentally changing the spawner type.

## Recommendations

**For Production Environments:**
- Only grant `docker-privileged` membership to administrators and DevOps personnel
- Document which users have socket access and why
- Regularly audit group membership through admin panel
- Enable Docker daemon logging and monitor for suspicious activity
- Consider separate JupyterHub instance for privileged users if many non-privileged users exist
- Ensure host system is hardened with latest security updates

**For Development/Research Environments:**
- Docker socket access can be granted more liberally to research teams
- Focus on data loss prevention rather than privilege escalation prevention
- Regular backups are more critical than access restrictions
- Clear usage policies help prevent accidental damage more than technical controls

Docker socket access is a powerful feature that enables advanced workflows while introducing security considerations. Understanding the implications helps administrators make informed decisions about access control for their specific environment.
