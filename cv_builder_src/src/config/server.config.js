const dotenv = require('dotenv');

dotenv.config();

module.exports = {
  PORT: process.env.PORT || 3000,
  logger_level: process.env.logger_level || 'info',
};
