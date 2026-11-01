# Fusion System Administrator — Client

React 18 + Vite SPA (Mantine v7) for the Fusion System Administrator. It renders inside a
Mantine `AppShell` (branded sidebar + top header), talks to the Django API at `/api`, and
is served under a configurable base path (`APP_BASE_PATH`, e.g. `/sysadmin/` in production).

## Develop

```bash
npm install
npm run dev        # http://localhost:5173 ; proxies /api -> http://localhost:8000
```

No local `.env` is required — the dev server proxies `/api` to the backend (see
`vite.config.js`). Auth uses an httpOnly cookie set by the API on login.

## Build

```bash
npm run build      # emits dist/ ; base path comes from APP_BASE_PATH in the repo-root .env
npm run lint
```

## Structure

```
src/
  api/          Axios API clients (axiosInstance + per-domain modules)
  components/   AppLayout (AppShell), PageHeader, RequireAuth
  context/      AuthContext, axiosInstance
  pages/        Dashboard, UserDirectory, UpcomingBatches, Role/User/Backup/Archive, Login
  theme.js      global Mantine theme
```

See the repository [README](../README.md), [SETUP.md](../SETUP.md), and
[DEPLOYMENT.md](../DEPLOYMENT.md) for full setup and deployment.
