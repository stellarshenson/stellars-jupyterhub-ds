"""HTTP admin API for the central proxy.

Three endpoints, all gated by a bearer token (shared secret in the env var
`STELLARS_PROXY_ADMIN_TOKEN`):

  GET    /admin/registered           -> 200 {"users": [{user, socket_path, config}, ...]}
  POST   /admin/registered/{user}    body: {overrides:{...}} -> 200 {"user","socket_path"}
  DELETE /admin/registered/{user}    -> 200 {"removed": bool}

Idempotency:
  - POST is "register or replace": if user already registered, the previous
    listener is torn down and a new one is started (so the operator can update
    quotas by re-posting).
  - DELETE is "remove if present": returns 200 either way with {"removed": bool}.

The admin API is the ONLY privileged surface. The data path (per-user unix
sockets) is unauthenticated by design - access is governed by which container
mounts which socket file. See manager.py.
"""

import json

from aiohttp import web


def _auth_required(token):
    @web.middleware
    async def middleware(request, handler):
        if request.path.startswith("/admin"):
            got = request.headers.get("Authorization", "")
            if got != f"Bearer {token}":
                return web.json_response({"error": "unauthorized"}, status=401)
        return await handler(request)
    return middleware


async def _list(request):
    manager = request.app["manager"]
    return web.json_response({"users": manager.registered()})


async def _register(request):
    manager = request.app["manager"]
    user = request.match_info["user"]
    body = {}
    if request.can_read_body:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "invalid_json"}, status=400)
    overrides = body.get("overrides") or {}
    try:
        socket_path = await manager.register(user, overrides=overrides)
    except (TypeError, ValueError) as e:
        return web.json_response({"error": "invalid_overrides", "message": str(e)},
                                 status=400)
    return web.json_response({"user": user, "socket_path": socket_path})


async def _unregister(request):
    manager = request.app["manager"]
    user = request.match_info["user"]
    removed = await manager.unregister(user)
    return web.json_response({"removed": removed})


def create_admin_app(manager, token):
    """Build the admin aiohttp app. `token` gates every /admin/* route."""
    if not token:
        raise ValueError("admin token is required")
    app = web.Application(middlewares=[_auth_required(token)])
    app["manager"] = manager
    app.router.add_get("/admin/registered", _list)
    app.router.add_post("/admin/registered/{user}", _register)
    app.router.add_delete("/admin/registered/{user}", _unregister)
    return app
