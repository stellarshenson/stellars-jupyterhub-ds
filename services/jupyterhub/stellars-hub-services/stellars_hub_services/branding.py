"""Custom branding setup - logo, favicon, JupyterLab icons."""

import os
import shutil
import sys


def setup_branding(logo_uri='', favicon_uri='', favicon_busy_uri='',
                   lab_main_icon_uri='', lab_splash_icon_uri=''):
    """Process branding URIs. Returns branding state dict.

    Args:
        logo_uri: JUPYTERHUB_LOGO_URI value (file:// or URL or empty)
        favicon_uri: JUPYTERHUB_FAVICON_URI value (file:// or URL or empty)
        favicon_busy_uri: JUPYTERHUB_FAVICON_BUSY_URI value (file:// or URL or empty).
            Overrides JupyterLab's kernel-busy favicon frames; empty leaves the
            busy frames served by the user's own JupyterLab server (default).
        lab_main_icon_uri: JUPYTERHUB_LAB_MAIN_ICON_URI value
        lab_splash_icon_uri: JUPYTERHUB_LAB_SPLASH_ICON_URI value

    Returns dict:
        logo_file: str or None - local path for c.JupyterHub.logo_file
        favicon_uri: str - external URL or '' (served from static after copy)
        favicon_busy_target: str - redirect target for busy frames: a hub-relative
            'hub/static/favicon-busy.ico' (file:// copied), an external URL, or ''
            (no override - busy frames fall through to the user server)
        lab_main_icon_static: str - static filename after copy (e.g., 'lab-main-icon.svg')
        lab_main_icon_url: str - external URL if not file://
        lab_splash_icon_static: str
        lab_splash_icon_url: str
    """
    static_dir = os.path.join(sys.prefix, 'share', 'jupyterhub', 'static')

    branding = {
        'logo_file': None,
        'favicon_uri': '',
        'favicon_busy_target': '',
        'lab_main_icon_static': '',
        'lab_main_icon_url': '',
        'lab_splash_icon_static': '',
        'lab_splash_icon_url': '',
    }

    # Logo
    if logo_uri.startswith('file://'):
        logo_file = logo_uri[7:]
        if os.path.exists(logo_file):
            branding['logo_file'] = logo_file

    # Favicon (idle frame)
    if favicon_uri.startswith('file://'):
        favicon_file = favicon_uri[7:]
        if os.path.exists(favicon_file):
            static_favicon = os.path.join(static_dir, 'favicon.ico')
            shutil.copy2(favicon_file, static_favicon)
        favicon_uri = ''  # Served via static_url after copy
    branding['favicon_uri'] = favicon_uri

    # Favicon (kernel-busy frames). file:// copies to hub static and the
    # redirect target is the hub-relative static path; an external URL is used
    # as the redirect target directly. Empty leaves busy frames to the user
    # server (JupyterLab default).
    if favicon_busy_uri.startswith('file://'):
        busy_file = favicon_busy_uri[7:]
        if os.path.exists(busy_file):
            shutil.copy2(busy_file, os.path.join(static_dir, 'favicon-busy.ico'))
            branding['favicon_busy_target'] = 'hub/static/favicon-busy.ico'
    elif favicon_busy_uri:
        branding['favicon_busy_target'] = favicon_busy_uri

    # Lab main icon
    if lab_main_icon_uri.startswith('file://'):
        icon_file = lab_main_icon_uri[7:]
        if os.path.exists(icon_file):
            ext = os.path.splitext(icon_file)[1] or '.svg'
            static_name = f'lab-main-icon{ext}'
            shutil.copy2(icon_file, os.path.join(static_dir, static_name))
            branding['lab_main_icon_static'] = static_name
    elif lab_main_icon_uri:
        branding['lab_main_icon_url'] = lab_main_icon_uri

    # Lab splash icon
    if lab_splash_icon_uri.startswith('file://'):
        icon_file = lab_splash_icon_uri[7:]
        if os.path.exists(icon_file):
            ext = os.path.splitext(icon_file)[1] or '.svg'
            static_name = f'lab-splash-icon{ext}'
            shutil.copy2(icon_file, os.path.join(static_dir, static_name))
            branding['lab_splash_icon_static'] = static_name
    elif lab_splash_icon_uri:
        branding['lab_splash_icon_url'] = lab_splash_icon_uri

    return branding
