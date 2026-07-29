require("dotenv").config();

function required(name) {
  const v = process.env[name];
  if (!v) {
    console.warn(`[config] ${name} is not set — routes depending on it will return 503`);
  }
  return v || null;
}

const DEV_SESSION_SECRET = "dev-secret-change-me";
const sessionSecret = process.env.SESSION_SECRET || DEV_SESSION_SECRET;

// A predictable session secret lets anyone forge session cookies. Refuse to
// boot in production rather than run with the placeholder.
if (process.env.NODE_ENV === "production") {
  if (!process.env.SESSION_SECRET || sessionSecret === DEV_SESSION_SECRET || sessionSecret === "change-me") {
    console.error("[config] SESSION_SECRET must be set to a strong random value in production. Refusing to start.");
    process.exit(1);
  }
  for (const name of ["GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET", "GITHUB_CALLBACK_URL", "FRONTEND_URL"]) {
    if (!process.env[name]) {
      console.error(`[config] ${name} must be set in production. Refusing to start.`);
      process.exit(1);
    }
  }
}

module.exports = {
  port: process.env.PORT || 4000,

  github: {
    clientId: required("GITHUB_CLIENT_ID"),
    clientSecret: required("GITHUB_CLIENT_SECRET"),
    callbackUrl: required("GITHUB_CALLBACK_URL"),
    scope: process.env.GITHUB_OAUTH_SCOPE || "public_repo",
  },

  google: {
    clientId: process.env.GOOGLE_CLIENT_ID || null,
    clientSecret: process.env.GOOGLE_CLIENT_SECRET || null,
    callbackUrl: process.env.GOOGLE_CALLBACK_URL || "http://localhost:4000/api/auth/google/callback",
  },

  frontendUrl: process.env.FRONTEND_URL || "http://localhost:5173",
  redisUrl: process.env.REDIS_URL || "redis://localhost:6379",
  sessionSecret,
};
