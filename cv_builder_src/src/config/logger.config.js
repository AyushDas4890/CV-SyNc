const pino = require('pino');
const path = require('path');
const { logger_level } = require('./server.config');
const logger = pino(
  {
    level: logger_level,
  },
  pino.transport({
    targets: [
      {
        target: 'pino-pretty',
        options: {
          colorize: true,
          translateTime: 'SYS:standard', // adds readable timestamp
          ignore: 'pid,hostname', // removes noise
        },
      },
      {
        target: 'pino-pretty',
        options: {
          destination: path.join(process.cwd(), 'app.log'),
          colorize: false,
          ignore: 'pid,hostname',
          translateTime: 'SYS:yyyy-mm-dd HH:MM:ss.l o',
        },
      },
    ],
  })
);
module.exports = logger;
