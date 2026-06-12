"""Hub-side file-download blocking (best-effort policy + notify + audit).

A user whose effective download policy is "block" - the highest-priority group
whose File Downloads section is on resolved to block, or no group configures it
and the platform JUPYTERHUB_BLOCK_FILE_DOWNLOADS default blocks - has per-user
CHP routes overlaid onto their lab's download surfaces, sending those prefixes
to the hub instead of the container (same mechanism as the favicon routes).
These handlers act on the overlaid traffic.

This is NOT a security boundary: the lab user is root in their container with
open egress, so a terminal/kernel `curl`/`scp` over an encrypted channel
bypasses any HTTP control. The value is stopping the browser download
affordances, telling the user it is policy, and leaving an audit trail. Inline
viewing, the contents API, kernels and terminals are deliberately untouched.

Two handlers:
- DownloadBlockHandler: pure-download prefixes (export-markdown export/*, the
  share-files public download links). Always 403 + notify + audit. Plain
  tornado handler (no auth) so it also blocks the unauthenticated public
  share link.
- FilesGuardHandler: mixed inline+download prefixes (files/*, nbconvert/*).
  Blocks when the request carries a truthy `download` arg (the only thing that
  makes jupyter_server emit Content-Disposition: attachment on these paths),
  otherwise reverse-proxies to the container so inline content keeps working.
"""

import json
import time

from tornado import web
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from ..docker_utils import encode_username_for_docker


# ── Notification throttle ────────────────────────────────────────────────────
# Per-user: at most one toast per window; blocks within the window are counted
# and the aggregate ("N downloads blocked") rides the next toast. monotonic
# clock so it is immune to wall-clock changes.
_NOTIFY_WINDOW_SECONDS = 10.0
# username -> {'last': monotonic_ts | None, 'suppressed': int}
_notify_state = {}


def _is_download_arg(value):
    """True when a `download` query arg means 'save to disk'.

    jupyter_server's FilesHandler sets the attachment header for any truthy
    download arg; NbconvertFileHandler for download==\"true\". Treat the usual
    falsy spellings as not-a-download so `?download=0` never blocks.
    """
    if value is None:
        return False
    return value.strip().lower() not in ('', '0', 'false', 'no', 'off')


def _wants_html(request):
    """Top-level navigation (Accept: text/html) gets an HTML page; API/fetch
    callers get JSON."""
    accept = request.headers.get('Accept', '')
    return 'text/html' in accept


_BLOCK_HTML = (
    "<!doctype html><html><head><meta charset='utf-8'>"
    "<title>Download blocked</title></head>"
    "<body style='font-family:sans-serif;max-width:40rem;margin:4rem auto;"
    "color:#222'><h2>Download blocked by policy</h2>"
    "<p>File downloads from this server are disabled by the administrator. "
    "Your work in the lab is unaffected.</p></body></html>"
)


async def notify_blocked(username, filename):
    """Push a throttled 'download blocked' toast to the user's lab.

    Fire-and-forget: callers schedule this without awaiting in the request
    path so the 403 is never delayed. Best-effort - a missing notifications
    extension or a stopped server simply means no toast.
    """
    from jupyterhub.app import JupyterHub

    now = time.monotonic()
    state = _notify_state.get(username) or {'last': None, 'suppressed': 0}
    if state['last'] is not None and (now - state['last']) < _NOTIFY_WINDOW_SECONDS:
        # Inside the window: count it, stay silent. The aggregate rides the
        # next toast once the window passes.
        state['suppressed'] += 1
        _notify_state[username] = state
        return
    suppressed = state['suppressed']
    _notify_state[username] = {'last': now, 'suppressed': 0}

    app = JupyterHub.instance()
    user = app.users.get(username) if app.users else None
    if user is None:
        return
    spawner = user.spawner
    if not (spawner and spawner.active and spawner.server):
        return

    if suppressed > 0:
        message = f"Download blocked by policy ({suppressed + 1} downloads blocked)"
    elif filename:
        message = f"Download blocked by policy: {filename}"
    else:
        message = "Download blocked by policy"

    payload = {
        "message": message[:140],
        "type": "warning",
        "autoClose": False,
        "actions": [{"label": "Dismiss", "caption": "Close this notification",
                     "displayType": "default"}],
    }

    try:
        token = user.new_api_token(note="download-blocked", expires_in=300)
        base_url = spawner.server.base_url
        container_url = f"http://jupyterlab-{encode_username_for_docker(username)}:8888"
        endpoint = f"{container_url}{base_url}jupyterlab-notifications-extension/ingest"
        request = HTTPRequest(
            url=endpoint,
            method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {token}"},
            body=json.dumps(payload),
            request_timeout=5.0,
            connect_timeout=5.0,
        )
        await AsyncHTTPClient().fetch(request, raise_error=False)
    except Exception as e:
        app.log.warning("[Downloads] notify failed user=%s: %s", username, e)


def _schedule_notify(username, filename):
    """Schedule notify_blocked on the IO loop without blocking the response."""
    from tornado.ioloop import IOLoop
    IOLoop.current().add_callback(notify_blocked, username, filename)


def _filename_from_path(subpath):
    """Last path segment for the toast, sans query/trailing slash."""
    if not subpath:
        return ''
    return subpath.rstrip('/').split('/')[-1]


# ── Pure-download prefixes: always 403 ───────────────────────────────────────
class DownloadBlockHandler(web.RequestHandler):
    """Block download-only endpoints unconditionally (export-markdown export/*,
    share-files public download links). No auth: these are always downloads and
    the share link is intentionally unauthenticated, so we 403 regardless of
    who asks. Injected outside the /hub/ prefix like FaviconRedirectHandler.
    """

    def initialize(self, **kwargs):
        # username and subpath come from the route capture groups.
        pass

    def _block(self, username, subpath):
        filename = _filename_from_path(subpath)
        # Audit + notify (notify is best-effort and never delays the 403).
        try:
            from jupyterhub.app import JupyterHub
            JupyterHub.instance().log.warning(
                "[Downloads] BLOCKED user=%s path=%s via=pure-download",
                username, subpath,
            )
        except Exception:
            pass
        _schedule_notify(username, filename)
        self.set_status(403)
        if _wants_html(self.request):
            self.set_header('Content-Type', 'text/html; charset=utf-8')
            self.finish(_BLOCK_HTML)
        else:
            self.set_header('Content-Type', 'application/json')
            self.finish(json.dumps({"error": "downloads_blocked"}))

    def get(self, username, subpath=''):
        self._block(username, subpath)

    def post(self, username, subpath=''):
        self._block(username, subpath)

    def head(self, username, subpath=''):
        self._block(username, subpath)


# ── Mixed prefixes: block on download intent, else reverse-proxy ─────────────
# Hop-by-hop response headers must not be relayed verbatim through the proxy.
_HOP_BY_HOP = {
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailers', 'transfer-encoding', 'upgrade', 'content-length',
}


class FilesGuardHandler(web.RequestHandler):
    """Guard files/* and nbconvert/* for a download-blocked user.

    Mounted at /user/{u}/... where the hub login cookie (scoped to /hub/) is
    never sent - so hub-side @web.authenticated is impossible here: it would
    302 to /hub/login, which (already authenticated there) 302s back to the
    file, looping forever (ERR_TOO_MANY_REDIRECTS). Instead block a truthy
    `download` arg (the only trigger for Content-Disposition: attachment on
    these paths) and reverse-proxy everything else to the user's container,
    forwarding the request cookies so the single-user server does its own auth.
    Cross-user access is structurally prevented: the browser only sends the
    /user/{u}/ cookie to that user's own prefix.
    """

    def initialize(self, **kwargs):
        # username and subpath come from the route capture groups.
        pass

    async def _guard(self, username, subpath):
        from jupyterhub.app import JupyterHub
        app = JupyterHub.instance()

        if _is_download_arg(self.get_argument('download', None)):
            filename = _filename_from_path(subpath)
            app.log.warning(
                "[Downloads] BLOCKED user=%s path=%s via=download-arg",
                username, subpath,
            )
            _schedule_notify(username, filename)
            self.set_status(403)
            if _wants_html(self.request):
                self.set_header('Content-Type', 'text/html; charset=utf-8')
                self.finish(_BLOCK_HTML)
            else:
                self.set_header('Content-Type', 'application/json')
                self.finish(json.dumps({"error": "downloads_blocked"}))
            return

        await self._proxy(username, subpath)

    async def _proxy(self, username, subpath):
        """Stream the container's response back to the browser.

        Forwards the request headers (incl. Cookie and Range) so the lab's own
        auth and 206 range handling apply. Defense-in-depth: if the container
        unexpectedly returns an attachment, convert it to a block before any
        body reaches the client.
        """
        from jupyterhub.app import JupyterHub
        app = JupyterHub.instance()
        user = app.users.get(username) if app.users else None
        spawner = user.spawner if user else None
        if not (spawner and spawner.active and spawner.server):
            raise web.HTTPError(503, "Server not available")

        container_url = f"http://jupyterlab-{encode_username_for_docker(username)}:8888"
        target = f"{container_url}{spawner.server.base_url}{subpath}"
        if self.request.query:
            target = f"{target}?{self.request.query}"

        # Forward request headers verbatim except Host (AsyncHTTPClient sets it
        # from the target) and Accept-Encoding (avoid relaying a compressed body
        # we would then mislabel).
        fwd_headers = {k: v for k, v in self.request.headers.get_all()
                       if k.lower() not in ('host', 'accept-encoding')}

        state = {'blocked': False, 'status_set': False}

        def header_callback(line):
            line = line.strip()
            if not line:
                return  # end of headers
            if line.startswith('HTTP/'):
                # Status line, e.g. "HTTP/1.1 206 Partial Content"
                try:
                    code = int(line.split(None, 2)[1])
                except (IndexError, ValueError):
                    code = 200
                state['_code'] = code
                return
            if ':' not in line:
                return
            name, _, value = line.partition(':')
            name = name.strip()
            value = value.strip()
            lname = name.lower()
            if lname == 'content-disposition' and 'attachment' in value.lower():
                # Should not happen on the inline branch, but never leak a
                # download: drop into block mode and suppress this header.
                state['blocked'] = True
                return
            if state['blocked']:
                return
            if lname in _HOP_BY_HOP:
                return
            if not state['status_set']:
                self.set_status(state.get('_code', 200))
                state['status_set'] = True
            self.add_header(name, value)

        def streaming_callback(chunk):
            if state['blocked']:
                return
            if not state['status_set']:
                self.set_status(state.get('_code', 200))
                state['status_set'] = True
            self.write(chunk)
            self.flush()

        request = HTTPRequest(
            url=target,
            method=self.request.method,
            headers=fwd_headers,
            body=self.request.body if self.request.method in ('POST', 'PUT', 'PATCH') else None,
            allow_nonstandard_methods=True,
            follow_redirects=False,
            request_timeout=120.0,
            connect_timeout=10.0,
            header_callback=header_callback,
            streaming_callback=streaming_callback,
        )
        try:
            await AsyncHTTPClient().fetch(request, raise_error=False)
        except Exception as e:
            app.log.error("[Downloads] proxy error user=%s path=%s: %s",
                          username, subpath, e)
            if not state['status_set']:
                raise web.HTTPError(502, "Upstream error")
            return

        if state['blocked']:
            filename = _filename_from_path(subpath)
            app.log.warning(
                "[Downloads] BLOCKED user=%s path=%s via=attachment-header",
                username, subpath,
            )
            _schedule_notify(username, filename)
            self.set_status(403)
            self.set_header('Content-Type', 'application/json')
            self.finish(json.dumps({"error": "downloads_blocked"}))
            return
        self.finish()

    async def get(self, username, subpath):
        await self._guard(username, subpath)

    async def head(self, username, subpath):
        await self._guard(username, subpath)

    async def post(self, username, subpath):
        await self._guard(username, subpath)
