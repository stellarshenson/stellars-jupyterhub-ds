"""Owner-scoping reverse proxy in front of the Docker socket.

Classifies each Docker API request and either mutates it (inject owner labels,
enforce caps/quota, narrow list/prune filters, guard actions by ownership) or
streams it straight through. Knows nothing about JupyterHub: the owner is a
plain string from config, or from an injected ``owner_resolver`` callable.
"""

import asyncio
import json
import logging
import os
import re

from aiohttp import ClientSession, ClientTimeout, UnixConnector, web

from . import filters as F
from . import quota as Q

log = logging.getLogger("stellars_docker_proxy")

# Strip a leading Docker API version prefix (e.g. "/v1.43") for classification;
# the original path (version included) is still what gets forwarded.
_VERSION_RE = re.compile(r"^/v\d+(?:\.\d+)?(?=/)")
_HOP_BY_HOP = {"transfer-encoding", "content-length", "content-encoding", "connection"}


def _strip_version(path):
    return _VERSION_RE.sub("", path, count=1)


def classify(method, path):
    """Return a tuple describing how to handle a request.

    ('list'|'create'|'prune', kind) | ('action', kind, id) |
    ('image_create',) | ('passthrough',)
    """
    p = _strip_version(path)

    if method == "GET" and p == "/containers/json":
        return ("list", "containers")
    if method == "POST" and p == "/containers/create":
        return ("create", "containers")
    if method == "POST" and p == "/containers/prune":
        return ("prune", "containers")
    m = re.match(r"^/containers/([^/]+)(?:/.*)?$", p)
    if m:
        return ("action", "containers", m.group(1))

    if method == "GET" and p == "/volumes":
        return ("list", "volumes")
    if method == "POST" and p == "/volumes/create":
        return ("create", "volumes")
    if method == "POST" and p == "/volumes/prune":
        return ("prune", "volumes")
    m = re.match(r"^/volumes/([^/]+)$", p)
    if m and method in ("GET", "DELETE"):
        return ("action", "volumes", m.group(1))

    if method == "GET" and p == "/networks":
        return ("list", "networks")
    if method == "POST" and p == "/networks/create":
        return ("create", "networks")
    if method == "POST" and p == "/networks/prune":
        return ("prune", "networks")
    m = re.match(r"^/networks/([^/]+)(?:/.*)?$", p)
    if m:
        return ("action", "networks", m.group(1))

    if method == "POST" and p == "/images/create":
        return ("image_create",)

    return ("passthrough",)


def _err(status, message):
    """Docker-style JSON error body."""
    return web.json_response({"message": message}, status=status)


class ProxyApp:
    """Per-owner request handler over a shared aiohttp ClientSession."""

    def __init__(self, config, session, owner_resolver=None):
        self.config = config
        self.session = session
        self.owner_resolver = owner_resolver

    async def _owner(self, request):
        if self.owner_resolver is not None:
            return await self.owner_resolver(request)
        return self.config.owner

    def _image_allowed(self, image):
        allow = self.config.image_allowlist
        if not allow:
            return True
        repo = (image or "").split(":")[0]
        return any(image == a or repo == a for a in allow)

    async def _inspect(self, kind, ident):
        paths = {
            "containers": f"/containers/{ident}/json",
            "volumes": f"/volumes/{ident}",
            "networks": f"/networks/{ident}",
        }
        async with self.session.get("http://docker" + paths[kind]) as r:
            if r.status != 200:
                return None
            try:
                return await r.json()
            except Exception:
                return None

    async def _count(self, kind, owner):
        params = {"filters": F.merge_label_filter(None, owner)}
        if kind == "containers":
            params["all"] = "1"
            url = "http://docker/containers/json"
        elif kind == "volumes":
            url = "http://docker/volumes"
        else:
            url = "http://docker/networks"
        async with self.session.get(url, params=params) as r:
            if r.status != 200:
                return 0
            data = await r.json()
        if kind == "volumes":
            return len((data or {}).get("Volumes") or [])
        return Q.list_count(data)

    async def _system_df(self):
        async with self.session.get("http://docker/system/df") as r:
            if r.status != 200:
                return {}
            try:
                return await r.json()
            except Exception:
                return {}

    async def handle(self, request):
        owner = await self._owner(request)
        if not owner:
            return _err(403, "no owner resolved for request")
        tag = classify(request.method, request.rel_url.path)
        try:
            if tag[0] == "create":
                return await self._handle_create(request, owner, tag[1])
            if tag[0] == "action":
                return await self._handle_action(request, owner, tag[1], tag[2])
            if tag[0] == "list":
                return await self._handle_list(request, owner, tag[1])
            if tag[0] == "prune":
                return await self._handle_prune(request, owner, tag[1])
            if tag[0] == "image_create":
                return await self._handle_image_create(request, owner)
            return await self._forward(request)
        except web.HTTPException:
            raise
        except Exception as e:  # never leak a traceback to the docker client
            log.exception("proxy error on %s %s", request.method, request.rel_url.path)
            return _err(502, f"proxy error: {e}")

    async def _handle_create(self, request, owner, kind):
        raw = await request.read()
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return _err(400, "invalid JSON body")
        if not isinstance(body, dict):
            return _err(400, "invalid request body")

        if kind == "containers":
            if self.config.block_dangerous:
                reason = F.dangerous_reason(body)
                if reason:
                    return _err(403, reason)
            cap_err = F.caps_violation(body, self.config.cpu_cap_cores, self.config.mem_cap_gb)
            if cap_err:
                return _err(403, cap_err)
            if not self._image_allowed(body.get("Image") or ""):
                return _err(403, f"image not allowed: {body.get('Image')}")

        maxes = {
            "containers": self.config.max_containers,
            "volumes": self.config.max_volumes,
            "networks": self.config.max_networks,
        }
        current = await self._count(kind, owner)
        if Q.over_count(current, maxes[kind]):
            return _err(403, f"{kind} quota reached ({maxes[kind]})")

        if kind in ("containers", "volumes") and self.config.max_storage_gb > 0:
            df = await self._system_df()
            if Q.over_storage_budget(df, owner, self.config.max_storage_gb):
                return _err(403, f"storage budget reached ({self.config.max_storage_gb} GB)")

        user_compose = F.has_compose_project(body)
        body = F.inject_labels(body, owner)
        query = dict(request.rel_url.query)
        if kind == "containers":
            # Group ad-hoc containers under the configured project; user's own
            # compose containers keep their project and their compose-set name.
            body = F.inject_compose_project(body, self.config.compose_project)
            body = F.apply_caps(body, self.config.cpu_cap_cores, self.config.mem_cap_gb)
            if not user_compose:
                new_name = F.ensure_name_prefix(query.get("name"), self.config.name_prefix)
                if new_name:
                    query["name"] = new_name

        return await self._forward(
            request,
            body=json.dumps(body).encode(),
            query=query,
            extra_headers={"Content-Type": "application/json"},
        )

    async def _handle_action(self, request, owner, kind, ident):
        inspect = await self._inspect(kind, ident)
        if inspect is None or not F.is_owned(inspect, owner):
            return _err(404, f"no such {kind[:-1]}: {ident}")
        return await self._forward(request)

    async def _handle_list(self, request, owner, kind):
        query = dict(request.rel_url.query)
        query["filters"] = F.merge_label_filter(query.get("filters"), owner)
        return await self._forward(request, query=query)

    async def _handle_prune(self, request, owner, kind):
        query = dict(request.rel_url.query)
        query["filters"] = F.merge_label_filter(query.get("filters"), owner)
        return await self._forward(request, query=query)

    async def _handle_image_create(self, request, owner):
        if self.config.image_allowlist:
            img = request.rel_url.query.get("fromImage") or ""
            tag = request.rel_url.query.get("tag") or ""
            full = f"{img}:{tag}" if tag else img
            if not self._image_allowed(img) and not self._image_allowed(full):
                return _err(403, f"image not allowed: {full or img}")
        return await self._forward(request)

    async def _forward(self, request, *, path=None, query=None, body=None, extra_headers=None):
        """Forward to the upstream daemon and stream the response back.

        Streaming covers logs --follow, pull/build progress, etc. Hijacked TTY
        streams (interactive `exec -it`/`attach`) are a known v1 limitation -
        non-interactive use is unaffected.
        """
        method = request.method
        fwd_path = path if path is not None else request.rel_url.path
        params = query if query is not None else dict(request.rel_url.query)
        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in _HOP_BY_HOP and k.lower() != "host"
        }
        if extra_headers:
            headers.update(extra_headers)

        if body is not None:
            data = body
        elif method in ("POST", "PUT", "PATCH"):
            data = request.content
        else:
            data = None

        resp = await self.session.request(
            method, "http://docker" + fwd_path, params=params, data=data, headers=headers
        )
        out = web.StreamResponse(status=resp.status)
        for k, v in resp.headers.items():
            if k.lower() in _HOP_BY_HOP:
                continue
            out.headers[k] = v
        await out.prepare(request)
        try:
            async for chunk in resp.content.iter_chunked(65536):
                await out.write(chunk)
        finally:
            resp.release()
        await out.write_eof()
        return out


async def create_app(config, owner_resolver=None):
    """Build the aiohttp application bound to the upstream Docker socket."""
    connector = UnixConnector(path=config.upstream_socket)
    session = ClientSession(connector=connector, timeout=ClientTimeout(total=None))
    proxy = ProxyApp(config, session, owner_resolver)
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", proxy.handle)

    async def _close(_app):
        await session.close()

    app.on_cleanup.append(_close)
    return app


async def run(config, owner_resolver=None):
    """Serve the per-owner filtered socket until cancelled."""
    app = await create_app(config, owner_resolver)
    runner = web.AppRunner(app)
    await runner.setup()
    try:
        os.unlink(config.listen_socket)
    except FileNotFoundError:
        pass
    site = web.UnixSite(runner, config.listen_socket)
    await site.start()
    # Who may reach the socket is governed by which container mounts it; the
    # socket itself is already owner-scoped, so it grants only this owner's view.
    os.chmod(config.listen_socket, getattr(config, "socket_mode", 0o666))
    log.info(
        "stellars-docker-proxy: owner=%s listen=%s upstream=%s",
        config.owner, config.listen_socket, config.upstream_socket,
    )
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await runner.cleanup()
