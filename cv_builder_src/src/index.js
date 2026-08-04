const express = require('express');
const cors = require('cors');
const { PORT } = require('./config/server.config');
const latexRouter = require('./router/latex.router');
const templateRouter = require('./router/template.router');
const logger = require('./config/logger.config');

const app = express();

app.use(cors());
app.use(express.json({ limit: '5mb' }));

// Liveness probe. Documented in the CV-Sync KB as already existing, but it
// never did — /api/health returned 404, so any container healthcheck pointed
// at it would mark this service permanently unhealthy and block anything
// depending on it from starting. Registered before the routers so it can never
// be shadowed by /api/:something.
app.get('/api/health', (req, res) => res.json({ ok: true, service: 'CV_BUILDER' }));

app.use('/api', latexRouter);
app.use('/api/templates', templateRouter);

app.listen(PORT, () => {
  logger.info(`server running on port : ${PORT}`);
});
