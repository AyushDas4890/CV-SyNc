const express = require("express");
const session = require("express-session");
const cors = require("cors");
const config = require("./config/env");
const githubAuthRoutes = require("./routes/githubAuth.routes");
const profileRoutes    = require("./routes/profile.routes");

const app = express();
app.use(express.json());

app.use(
  cors({
    origin: config.frontendUrl,
    credentials: true,
  })
);

process.on("unhandledRejection", (reason) => {
  console.error("[unhandledRejection]", reason?.message || reason);
});
process.on("uncaughtException", (err) => {
  if (err.code === "EPIPE" || err.code === "ERR_STREAM_DESTROYED") return;
  console.error("[uncaughtException]", err.message);
});
process.stdout?.on?.("error", () => {});
process.stderr?.on?.("error", () => {});

// Keep-alive timer to prevent premature process termination when background subshell detaches
setInterval(() => {}, 1000 * 60 * 60);

app.get("/api/health", (req, res) => res.json({ ok: true }));

async function startServer() {
  let sessionStore;

  if (process.env.USE_REDIS === "true") {
    try {
      const { createClient } = require("redis");
      const RedisStore = require("connect-redis").default;
      const redisClient = createClient({
        url: config.redisUrl,
        socket: { connectTimeout: 1000 },
      });
      redisClient.on("error", (err) => console.error("[redis] error:", err.message));
      await redisClient.connect();
      sessionStore = new RedisStore({ client: redisClient });
      console.log("[redis] Connected to Redis session store");
    } catch (err) {
      console.warn("[redis] Connection failed — using MemoryStore fallback.");
    }
  } else {
    console.log("[session] Using MemoryStore for development.");
  }

  app.use(
    session({
      store: sessionStore, // undefined = express-session MemoryStore
      secret: config.sessionSecret,
      resave: false,
      saveUninitialized: false,
      cookie: {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        maxAge: 1000 * 60 * 60 * 24, // 24h
      },
    })
  );

  if (process.env.NODE_ENV !== "production") {
    app.post("/dev/login", (req, res) => {
      req.session.userId = req.body.userId || "dev-user-1";
      res.json({ ok: true, userId: req.session.userId });
    });
  }

  app.use("/api/auth",    githubAuthRoutes);
  app.use("/api/profile", profileRoutes);

  const server = app.listen(config.port, () => {
    console.log(`auth-service listening on :${config.port}`);
  });

  server.on("error", (err) => {
    if (err.code === "EADDRINUSE") {
      console.error(`[server] Port ${config.port} is already in use by another process.`);
    } else {
      console.error("[server] Error:", err.message);
    }
  });
}

startServer();

