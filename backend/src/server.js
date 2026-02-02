require('dotenv').config();

const session = require('express-session');
const cookieParser = require('cookie-parser');
const passport = require('./config/passport');
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const http = require('http');
const db = require('./config/database');

const app = express();
const server = http.createServer(app);

// Get port from environment
const PORT = process.env.PORT || 5001;

// Simple logger using console
const logger = {
  info: (msg) => console.log(`ℹ️  ${msg}`),
  error: (msg, err) => console.error(` ${msg}`, err || '')
};

// Middleware
app.use(helmet());
app.use(cors({
  origin: 'http://localhost:3000',
  credentials: true
}));
app.use(compression());
app.use(express.json());
// Session configuration
app.use(cookieParser());
app.use(session({
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: process.env.NODE_ENV === 'production',
    httpOnly: true,
    maxAge: 24 * 60 * 60 * 1000 // 24 hours
  }
}));

// Passport initialization
app.use(passport.initialize());
app.use(passport.session());

app.use(express.urlencoded({ extended: true }));

// Health check route
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    service: 'backend',
    port: PORT,
    database: db.sequelize.authenticate() ? 'connected' : 'disconnected',
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
  
    await db.sequelize.authenticate();
    logger.info('Database connected');
    await db.sequelize.sync({ alter: true });
    logger.info('Database models synced');

    server.listen(PORT, () => {
      logger.info(` Server running on port ${PORT}`);
      logger.info(` Health check: http://localhost:${PORT}/health`);
    });
  } catch (error) {
    logger.error(' Unable to start server:', error);
    process.exit(1);
  }
};

const authRoutes = require('./routes/auth');
app.use('/api/v1/auth', authRoutes);

const analysisRoutes = require('./routes/analysis');
app.use('/api/v1/analysis', analysisRoutes);
startServer();

module.exports = { app, server };