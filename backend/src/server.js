require('dotenv').config();
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const http = require('http');

const app = express();
const server = http.createServer(app);

// Get port from environment
const PORT = process.env.PORT || 5001;

// Simple logger using console
const logger = {
  info: (msg) => console.log(`ℹ️  ${msg}`),
  error: (msg, err) => console.error(`❌ ${msg}`, err || '')
};

// Middleware
app.use(helmet());
app.use(cors());
app.use(compression());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Health check route
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    service: 'backend',
    port: PORT,
    timestamp: new Date().toISOString()
  });
});

// Root route
app.get('/', (req, res) => {
  res.json({ 
    message: 'CodeSage Backend API',
    version: '1.0.0',
    endpoints: {
      health: '/health',
      api: '/api/v1'
    }
  });
});

// Start server
const startServer = async () => {
  try {
    // Database connection commented out for now
    // await sequelize.authenticate();
    // logger.info('✅ Database connection established successfully');
    
    server.listen(PORT, () => {
      logger.info(`🚀 Server running on port ${PORT}`);
      logger.info(`📍 Health check: http://localhost:${PORT}/health`);
    });
  } catch (error) {
    logger.error('❌ Unable to start server:', error);
    process.exit(1);
  }
};

startServer();

module.exports = { app, server };