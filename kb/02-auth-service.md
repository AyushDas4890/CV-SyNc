# Auth service (designed, not coded)

Session-based. MySQL users + Redis sessions. Excalidraw: session-auth-corrected.excalidraw.

Flow:
- entry: client → reverse proxy → rate limiter (token bucket) → routes
- /signup: validate → argon2id hash → store user → create Redis session (TTL) → Set-Cookie LAST
- /signin: lookup email → found: argon2.verify(pw, hash) → session → cookie. NOT found: DUMMY argon2 verify anyway → generic 401. Same timing + same error both fail paths = no user enumeration
- /protected: cookie → session_id → Redis lookup (exists + not expired) → controller → service → DB. Else 401
- /logout: DELETE Redis session (critical, not only cookie) + clear cookie (Max-Age=0)

Rules:
- cookie holds ONLY opaque random session_id. HttpOnly, Secure, SameSite=Lax. Never email/password/role in cookie
- all session data server-side in Redis keyed by session_id

Schema users: id INT PK AI, email VARCHAR UNIQUE, password_hash VARCHAR (argon2id), role ENUM(admin,user), created_at TIMESTAMP.

GitHub identity SEPARATE from auth identity: nullable github_token + github_username cols (or github_accounts table), filled by later "Connect GitHub" OAuth (public_repo scope). V1 no OAuth: user paste repo links, server use own PAT from .env.

Build order (risk-first): E2E spike (signup→cookie→protected, ~100 lines) BEFORE middlewares. Pass checks in 06-build-plan.
