# Auth service (DONE — 2026-07-22)

Session-based. In-memory `userStore.service.js` for now (TODO: MySQL `users` table). MemoryStore sessions in dev (no Redis needed to run locally — falls back automatically). Redis optional via `USE_REDIS=true`.

## Routes (all mounted under /api/auth, /api/profile)

| Method | Path | Description |
|---|---|---|
| GET | /api/auth/github | GitHub OAuth redirect |
| GET | /api/auth/github/callback | Exchange code → session, redirect to /onboarding/profile |
| GET | /api/auth/me | Returns public profile of logged-in user |
| POST | /api/auth/logout | Destroys session + clears cookie |
| GET | /api/auth/github/repos | Lists GitHub repos for logged-in user |
| POST | /api/auth/email/register | bcryptjs (12 rounds) hash, 201 + session |
| POST | /api/auth/email/login | Verify hash, session |
| POST | /api/profile | Save studentProfile (profile + education) to user object |
| GET | /api/profile | Return saved studentProfile or null |

## userStore.service.js
- In-memory Maps: `usersById`, `byGithubId`, `byGoogleId`, `byEmail`
- Functions: `findOrCreateByGithubId`, `findOrCreateByGoogleId`, `createEmailUser`, `verifyEmailUser`, `getById`, `getGithubToken`, `publicProfile` (strips secrets), `saveProfile`, `getProfile`
- `user.studentProfile` = `{ profile: {fullName, phone, email, githubUrl, linkedinUrl}, education: [{institution, degree, fieldOfStudy, dates, gpa}], achievements: [{title, description, date}], certificates: [{name, issuer, date, link}], updatedAt }`

## Session rules
- Cookie: opaque session_id only. HttpOnly, Secure (prod), SameSite=Lax
- `session.regenerate()` called on login (session fixation prevention)
- Logout: `session.destroy()` + cookie cleared
- 24h maxAge cookie

## Auth surface
- GitHub OAuth = primary (recommended). Redirects to /onboarding/profile on success.
- Email/password = secondary. bcryptjs, 12 rounds. Register → 201 + session. Login → session.
- Google OAuth = code present (googleAuth.controller.js + googleAuth.service.js) but NOT mounted in router. Intentionally inert — frontend shows \"coming soon\".

## Profile+Education storage (2026-07-22)
- POST /api/profile: saves `{ profile, education }` onto `user.studentProfile` in userStore
- GET /api/profile: returns `user.studentProfile` or null
- Frontend ProfilePage.jsx: on mount calls GET /api/profile to pre-fill form; on Continue calls POST /api/profile to persist, also mirrors to localStorage under `cv_sync_student_profile`

## Files
- `src/server.js` — mounts /api/auth + /api/profile, session setup, dev /login shortcut
- `src/routes/githubAuth.routes.js` — all /api/auth routes
- `src/routes/profile.routes.js` — GET/POST /api/profile
- `src/controllers/githubAuth.controller.js` — login, callback, me, logout, repos
- `src/controllers/emailAuth.controller.js` — register, login
- `src/controllers/profile.controller.js` — save, get
- `src/services/githubAuth.service.js` — state gen, authorizeUrl, token exchange, fetch user
- `src/services/userStore.service.js` — unified in-memory user store + profile store
- `src/config/env.js` — env var validation, all config exported from one place
