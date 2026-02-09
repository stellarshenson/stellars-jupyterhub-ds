"""Docker utility functions for container and volume operations."""

import asyncio
from concurrent.futures import ThreadPoolExecutor

_docker_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="docker-ops")


def encode_username_for_docker(username):
    """Encode username for Docker volume/container names.

    Uses escapism library (same as DockerSpawner) for compatibility.
    e.g., 'user.name' -> 'user-2ename' (. = ASCII 46 = 0x2e)
    """
    from escapism import escape
    return escape(username, escape_char='-').lower()


def get_container_stats(username):
    """Get CPU and memory stats for a user's container (blocking)."""
    try:
        import docker
        docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        container_name = f'jupyterlab-{encode_username_for_docker(username)}'

        try:
            container = docker_client.containers.get(container_name)
            stats = container.stats(stream=False)

            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                        stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                           stats['precpu_stats']['system_cpu_usage']

            cpu_percent = 0.0
            if system_delta > 0 and cpu_delta > 0:
                online_cpus = stats['cpu_stats'].get('online_cpus', 1)
                cpu_percent = (cpu_delta / system_delta) * online_cpus * 100

            memory_usage = stats['memory_stats'].get('usage', 0)
            memory_limit = stats['memory_stats'].get('limit', 1)
            memory_percent = (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0

            return {
                'cpu_percent': round(cpu_percent, 1),
                'memory_mb': round(memory_usage / (1024 * 1024), 1),
                'memory_percent': round(memory_percent, 1),
            }
        finally:
            docker_client.close()
    except Exception:
        return None


async def get_container_stats_async(username):
    """Async wrapper - runs in thread pool to avoid blocking."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_docker_executor, get_container_stats, username)


def get_executor():
    """Return the shared thread pool executor for Docker operations."""
    return _docker_executor
