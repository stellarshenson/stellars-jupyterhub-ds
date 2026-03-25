"""Unauthenticated health check endpoint for monitoring systems (Zabbix, Prometheus, etc.).

Rate-limited to 1 request per second per IP to prevent abuse.
"""

import time
from collections import defaultdict

import jupyterhub
from jupyterhub.handlers import BaseHandler
from tornado import web

# Hub start time (module load = hub startup)
_start_time = time.time()

# Rate limiting: {ip: last_request_time}
_rate_limit = defaultdict(float)
_RATE_LIMIT_INTERVAL = 1.0  # seconds between allowed requests per IP


class HealthCheckHandler(BaseHandler):
    """GET /health - returns JSON with hub status, uptime, version, and server counts.

    Unauthenticated - designed for external monitoring agents.
    Rate-limited to 1 req/s per source IP.
    """

    def check_xsrf_cookie(self):
        """Skip XSRF check for monitoring agents."""

    async def get(self):
        # Rate limiting per source IP
        ip = self.request.remote_ip
        now = time.time()
        if now - _rate_limit[ip] < _RATE_LIMIT_INTERVAL:
            self.set_status(429)
            self.set_header('Retry-After', '1')
            self.finish({'error': 'Too many requests', 'retry_after': 1})
            return
        _rate_limit[ip] = now

        # Prune stale IPs (older than 60s) to prevent memory leak
        stale = [k for k, v in _rate_limit.items() if now - v > 60]
        for k in stale:
            del _rate_limit[k]

        uptime_seconds = int(now - _start_time)
        days, rem = divmod(uptime_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)

        # Count active servers
        active_servers = 0
        total_users = 0
        try:
            from jupyterhub import orm
            all_users = self.db.query(orm.User).all()
            total_users = len(all_users)
            for user in all_users:
                if user.running:
                    active_servers += 1
        except Exception:
            pass

        stellars_version = self.settings.get('template_vars', {}).get('stellars_version', 'unknown')

        self.set_header('Content-Type', 'application/json')
        self.set_header('Cache-Control', 'no-cache, no-store')
        self.finish({
            'status': 'ok',
            'uptime_seconds': uptime_seconds,
            'uptime': f'{days}d {hours}h {minutes}m',
            'version': {
                'stellars': stellars_version,
                'jupyterhub': jupyterhub.__version__,
            },
            'users': {
                'total': total_users,
                'active_servers': active_servers,
            },
        })
