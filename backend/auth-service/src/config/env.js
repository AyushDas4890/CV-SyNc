require("dotenv").config();

function required(name) {
  const v = process.env[name];
  if (!v) {
    // fail loud at boot, not at first request — matches teammate's PORT-fallback bug lesson (03-compiler-service.md)
    console.warn(`[config] ${name} is not set — GitHub OAuth routes will fail until it is`);
  }
  return v;
}

module.exports = {
  port: process.env.PORT || 4000,
  github: {
    clientId: required("GITHUB_CLIENT_ID"),
    clientSecret: required("GITHUB_CLIENT_SECRET"),
    callbackUrl: required("GITHUB_CALLBACK_URL"),
    scope: process.env.GITHUB_OAUTH_SCOPE || "public_repo",
  },
  frontendUrl: process.env.FRONTEND_URL || "http://localhost:5173",
  redisUrl: process.env.REDIS_URL || "redis://localhost:6379",
  sessionSecret: process.env.SESSION_SECRET || "dev-secret-change-me",
};
