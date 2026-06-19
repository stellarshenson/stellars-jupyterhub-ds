"""API keys pool: hand a finite set of credentials to user containers.

A group config may define a pool of API credentials. When a user's JupyterLab
container spawns, one free credential from each of the user's groups' pools is
injected into configured environment variables, such that **no two running
containers hold the same credential**. On stop the credential returns to the
pool. The pool is resilient: the in-use set is rebuilt by inspecting the actual
**running containers** (a durable Docker label carries the assigned slot id),
not by trusting stop events - so a container stopped while the hub was down, or
started by a previous hub version, self-heals on the next observation.

Design mirrors `idle_culler.py` / `docker_proxy.py`: a stdlib-only pure layer
(trivially unit-testable as scenario matrices), a runtime observation layer that
reads Docker off the main loop, a singleton `PoolManager` that closes the
assign-time race, and scheduled reconciliation callbacks. Heavy imports (docker,
jupyterhub, tornado) are done inside the runtime functions so importing this
module pulls in only the standard library.

Key facts:
- Durable marker = Docker label `tech.stellars.apikeys.pool.<group>.slot=<slot>`
  on the spawned container - the slot id only, never the secret.
- Each credential carries a stable `slot` id (minted by the handler on save),
  independent of list position, so admin reorder/edit never reassigns live
  containers.
- One pool per group; a user in N groups draws from N pools independently.
- Assignment takes effect at container **create** only (env vars can only be
  injected then). A user added to a group while already running gets keys at
  next spawn - same as every other group setting.
- Exhaustion: the configured env vars are still set, but empty, and a warning is
  logged. Assignments are logged showing only the last 4 chars of id/secret/key.
"""

import asyncio
import threading


# ── Label scheme (durable, version-independent marker) ───────────────────────

APIKEYS_LABEL_PREFIX = 'tech.stellars.apikeys.pool.'
APIKEYS_LABEL_SUFFIX = '.slot'


def pool_label_key(pool_id):
    """Docker label key carrying the assigned slot id for one pool on a container."""
    return f'{APIKEYS_LABEL_PREFIX}{pool_id}{APIKEYS_LABEL_SUFFIX}'


def parse_pool_labels(labels):
    """Extract `{pool_id: slot_id}` from a container's labels (pure).

    Matches every `tech.stellars.apikeys.pool.*.slot` label. Containers with no
    such label (legacy / pre-feature / started by another hub version) yield an
    empty dict and are therefore treated as holding no pool slot.
    """
    out = {}
    for key, val in (labels or {}).items():
        if key.startswith(APIKEYS_LABEL_PREFIX) and key.endswith(APIKEYS_LABEL_SUFFIX):
            pool_id = key[len(APIKEYS_LABEL_PREFIX):-len(APIKEYS_LABEL_SUFFIX)]
            if pool_id:
                out[pool_id] = val
    return out


# ── Pure layer (stdlib only, seconds/strings in - strings out) ───────────────

def mask_last4(value):
    """Masked representation for logs and API responses - never the full value."""
    if not value:
        return '****'
    return '****' + str(value)[-4:]


def new_slot():
    """Mint a fresh stable slot id (independent of list position)."""
    import uuid
    return uuid.uuid4().hex[:12]


def normalize_pool(pool_cfg):
    """Shape one group's stored `api_keys_pool` into a runtime descriptor.

    Returns None when the pool is disabled, has an invalid mode, or configures
    no target env var name (nothing to inject). A pool with valid target names
    but zero usable credentials is still returned - members then get the vars
    set empty (exhaustion), which is the intended behaviour.
    """
    if not pool_cfg or not pool_cfg.get('enabled'):
        return None
    mode = pool_cfg.get('mode')
    if mode not in ('pair', 'single'):
        return None
    if not (pool_cfg.get('env_var_id') or pool_cfg.get('env_var_secret') or pool_cfg.get('env_var_key')):
        return None

    creds = {}
    slot_ids = []
    for c in (pool_cfg.get('credentials') or []):
        slot = c.get('slot')
        if not slot:
            continue
        if mode == 'pair':
            if not c.get('id') or not c.get('secret'):
                continue
            creds[slot] = {'id': c['id'], 'secret': c['secret']}
        else:
            if not c.get('key'):
                continue
            creds[slot] = {'key': c['key']}
        if slot not in slot_ids:
            slot_ids.append(slot)

    return {
        'mode': mode,
        'env_var_id': pool_cfg.get('env_var_id', '') or '',
        'env_var_secret': pool_cfg.get('env_var_secret', '') or '',
        'env_var_key': pool_cfg.get('env_var_key', '') or '',
        'creds': creds,
        'slot_ids': slot_ids,
    }


def pick_free_slot(slot_ids, in_use, reserved):
    """First configured slot not already in use or tentatively reserved, else None.

    Ranks only over configured `slot_ids` (config order), so an orphan slot held
    by a running container after its credential was removed can never be
    re-handed-out. Returns None on exhaustion.
    """
    blocked = set(in_use) | set(reserved)
    for slot in slot_ids:
        if slot not in blocked:
            return slot
    return None


def env_for_slot(pool, slot_id):
    """Env var mapping for an assigned slot; all-empty on exhaustion/unknown slot."""
    cred = pool.get('creds', {}).get(slot_id) if slot_id else None
    out = {}
    if pool.get('mode') == 'pair':
        name_id = pool.get('env_var_id', '')
        name_secret = pool.get('env_var_secret', '')
        if name_id:
            out[name_id] = cred['id'] if cred else ''
        if name_secret:
            out[name_secret] = cred['secret'] if cred else ''
    else:
        name_key = pool.get('env_var_key', '')
        if name_key:
            out[name_key] = cred['key'] if cred else ''
    return out


def assignment_mask_str(pool, slot_id):
    """One-line masked summary for the assignment log (last 4 chars only)."""
    if slot_id is None:
        return 'EXHAUSTED'
    cred = pool.get('creds', {}).get(slot_id)
    if not cred:
        return '****'
    if pool.get('mode') == 'pair':
        return f"id={mask_last4(cred['id'])} secret={mask_last4(cred['secret'])}"
    return f"key={mask_last4(cred['key'])}"


def merge_pool_on_save(incoming, existing, slot_factory=None):
    """Shape an incoming pool (from the admin UI) for storage.

    The groups page is admin-only and shows credentials in full, so a save
    carries the real values back and they are stored verbatim. Existing
    credentials keep their stable `slot` id (so a running container's durable
    label stays valid); new entries get a freshly minted slot. Secrets are only
    ever obfuscated in logs (last-4), never in this admin-facing store/UI path.
    """
    if slot_factory is None:
        slot_factory = new_slot
    incoming = incoming or {}
    existing = existing or {}
    mode = incoming.get('mode', '') or ''
    existing_slots = {c.get('slot') for c in (existing.get('credentials') or []) if c.get('slot')}
    fields = ('id', 'secret') if mode == 'pair' else ('key',)

    out_creds = []
    for c in (incoming.get('credentials') or []):
        slot = c.get('slot')
        new_c = {'slot': slot if (slot and slot in existing_slots) else slot_factory()}
        for f in fields:
            new_c[f] = c.get(f) or ''
        new_c['description'] = c.get('description') or ''
        out_creds.append(new_c)

    return {
        'enabled': bool(incoming.get('enabled')),
        'mode': mode,
        'env_var_id': (incoming.get('env_var_id') or '').strip(),
        'env_var_secret': (incoming.get('env_var_secret') or '').strip(),
        'env_var_key': (incoming.get('env_var_key') or '').strip(),
        'credentials': out_creds,
    }


# ── Runtime observation layer (heavy imports done lazily) ────────────────────

def _list_running_pool_slots():
    """Blocking: derive the in-use set from running `jupyterlab-*` containers.

    Returns `(by_pool, by_container)`:
      by_pool       -> {pool_id: set(slot_id)}   (authoritative in-use set)
      by_container  -> {container_name: {pool_id: slot_id}}  (for per-user reuse)
    On any Docker error returns empties (assignment still proceeds; the periodic
    reconcile converges later).
    """
    by_pool = {}
    by_container = {}
    try:
        import docker
        from .docker_utils import encoded_username_from_lab_container
        client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        try:
            for c in client.containers.list(filters={'status': 'running'}):
                name = c.name or ''
                if encoded_username_from_lab_container(name) is None:
                    continue
                pls = parse_pool_labels(c.labels or {})
                if not pls:
                    continue
                by_container[name] = pls
                for pid, slot in pls.items():
                    by_pool.setdefault(pid, set()).add(slot)
        finally:
            client.close()
    except Exception:
        return {}, {}
    return by_pool, by_container


async def observe_in_use():
    """Async wrapper around `_list_running_pool_slots` (runs off the main loop)."""
    from .docker_utils import get_executor
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(get_executor(), _list_running_pool_slots)


def _container_name(username):
    from .docker_utils import lab_container_name
    return lab_container_name(username)


# ── PoolManager singleton (closes the assign-time race) ──────────────────────

class PoolManager:
    """Process-local arbiter of slot assignments.

    `observe_in_use` can only see a container **after** it is created, but the
    label/env must be decided **before** create. Two simultaneous spawns would
    otherwise both pick the same free slot. An asyncio lock plus a tentative
    reservation set closes that window; the durable container label then becomes
    the source of truth and the tentative entries are reaped on stop/reconcile.

    Note: the guarantee is hub-process-local. A single-hub deployment makes a
    transient double-assignment across two hub processes a non-issue; the
    label-derived reconcile would still converge.
    """

    _instance = None
    _singleton_lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._lock = asyncio.Lock()
        self._tentative = {}        # pool_id -> set(slot_id)
        self._tentative_user = {}   # (pool_id, username) -> slot_id

    async def assign(self, username, pools):
        """Assign one slot per pool for `username`'s spawning container.

        `pools` is the priority-ordered list of normalized pool descriptors from
        the resolver (each carries a `pool_id`, and a `group_index` where lower =
        higher priority). Returns `{'env': {var: value}, 'env_sources': {var:
        group_index}, 'labels': {label_key: slot}, 'assignments': [...]}`. Within
        the env map, the first pool to claim a var name wins (pools are
        priority-ordered), so a higher-priority group shadows a lower one;
        `env_sources` lets the caller resolve a pool-var vs plain-env-var clash by
        the same group order.
        """
        cname = _container_name(username)
        async with self._lock:
            by_pool, by_container = await observe_in_use()
            this_container = by_container.get(cname, {})

            env = {}
            env_sources = {}
            labels = {}
            assignments = []
            for pool in pools:
                pid = pool['pool_id']
                in_use = set(by_pool.get(pid, set())) | set(self._tentative.get(pid, set()))

                # Reuse this user's existing slot (their still-running container,
                # or an in-flight tentative) rather than allocating a second one.
                existing = None
                if this_container.get(pid) in pool['creds']:
                    existing = this_container.get(pid)
                else:
                    cand = self._tentative_user.get((pid, username))
                    if cand in pool['creds']:
                        existing = cand

                slot = existing if existing is not None else pick_free_slot(pool['slot_ids'], in_use, set())

                if slot is not None:
                    self._tentative.setdefault(pid, set()).add(slot)
                    self._tentative_user[(pid, username)] = slot
                    labels[pool_label_key(pid)] = slot

                for name, value in env_for_slot(pool, slot).items():
                    if name in env:
                        continue  # higher-priority pool already claimed this var
                    env[name] = value
                    env_sources[name] = pool.get('group_index', 0)

                assignments.append({
                    'pool_id': pid,
                    'slot': slot,
                    'masked': assignment_mask_str(pool, slot),
                })
            return {'env': env, 'env_sources': env_sources, 'labels': labels, 'assignments': assignments}

    def release_tentative(self, username):
        """Drop all in-flight reservations for a user (best-effort, on stop).

        The real release is the container leaving `observe_in_use()`; this just
        clears the short-lived tentative bookkeeping so a stopped-before-create
        spawn does not pin a slot.
        """
        for key in [k for k in self._tentative_user if k[1] == username]:
            pid, _ = key
            slot = self._tentative_user.pop(key, None)
            if slot is not None:
                self._tentative.get(pid, set()).discard(slot)

    async def reconcile(self):
        """Re-derive in-use from running containers and reap stale tentatives.

        A tentative entry is dropped once its slot appears on a real running
        container (promoted to a durable label) or once the user has no running
        container (spawn failed / already stopped). Returns a small summary dict
        for logging. The label-derived set always wins.
        """
        async with self._lock:
            by_pool, by_container = await observe_in_use()
            reaped = 0
            for key in list(self._tentative_user):
                pid, user = key
                slot = self._tentative_user[key]
                cname = _container_name(user)
                observed_for_user = by_container.get(cname, {})
                promoted = observed_for_user.get(pid) == slot or slot in by_pool.get(pid, set())
                gone = cname not in by_container
                if promoted or gone:
                    self._tentative_user.pop(key, None)
                    self._tentative.get(pid, set()).discard(slot)
                    reaped += 1
            in_use_total = sum(len(v) for v in by_pool.values())
            return {'pools': len(by_pool), 'in_use': in_use_total, 'reaped': reaped}
