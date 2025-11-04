# Release v3.0.14

## Major Features

**User Self-Service Capabilities**
- **Restart Server**: Users can restart their running JupyterLab containers directly from the control panel without admin intervention
- **Manage Volumes**: Selective reset of persistent volumes (home/workspace/cache) when server is stopped - users choose which volumes to reset via checkbox interface

## Technical Improvements

**Frontend**
- Bootstrap 5 modal compatibility (data-bs-toggle, data-bs-target, btn-close)
- RequireJS module loading for proper JavaScript execution
- Font Awesome icons (fa-rotate for restart, fa-database for volumes)
- Proper template inheritance extending JupyterHub's default home.html

**Backend**
- New API endpoint: `/api/users/{username}/manage-volumes` accepting JSON body with volume array
- ManageVolumesHandler processes multiple volumes with detailed success/failure response
- Manual permission checking (admin or self) for API handlers
- Comprehensive logging for all operations (frontend console + backend logs)

**Infrastructure**
- Version management system with project.env and auto-increment on build
- Makefile enhancements: increment_version, tag, stop, logs targets
- Docker API integration via /var/run/docker.sock for volume and container management

## Documentation

- README updated with Features section and visual screenshots
- CLAUDE.md created with architecture overview and configuration patterns
- FEATURE_PLAN.md documenting implementation strategy
- Journal tracking all substantive work

## Version History

- **v3.0.14**: Documentation updates, 3-second stop delay
- **v3.0.12**: Multi-volume management, Bootstrap 5 fixes, icons
- **v2.11**: Previous stable release

## Upgrade Notes

No breaking changes. Existing deployments will seamlessly adopt new self-service features upon container restart.

Users will see new buttons on the JupyterHub control panel:
- "Restart Server" (when server is running)
- "Manage Volumes" (when server is stopped)

---

**From**: v2.11-cuda-12.9.1
**To**: v3.0.14_cuda-12.9.1_jh-5.4.2
**Date**: 2025-11-04
