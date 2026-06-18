# Stock JupyterHub UI, for side-by-side comparison with the Duoptimum Hub portal.
#
# Dummy auth (any username, no password) so the stock home / admin pages render
# without real spawning - the point is to eyeball the STOCK design + functionality
# the duoptimum-hub portal replaced, not to run real labs. Log in as 'admin' to see
# the stock admin React app (the screen our Servers / Users portal replaced).

c.JupyterHub.authenticator_class = "dummy"
c.Authenticator.allow_all = True
c.Authenticator.admin_users = {"admin"}
c.JupyterHub.bind_url = "http://0.0.0.0:8000"
c.JupyterHub.base_url = "/"

# The default LocalProcessSpawner cannot actually spawn here (no system users);
# that is fine - the home + admin + user-management UI all render for comparison.
