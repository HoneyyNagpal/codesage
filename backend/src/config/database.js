const { Sequelize } = require('sequelize');

const sequelize = new Sequelize(process.env.DATABASE_URL, {
  dialect: 'postgres',
  logging: false,
  pool: {
    max: 5,
    min: 0,
    acquire: 30000,
    idle: 10000
  }
});

const db = {};
db.Sequelize = Sequelize;
db.sequelize = sequelize;

// Import models
db.Analysis = require('../models/Analysis')(sequelize);
db.User = require('../models/User')(sequelize);

db.User.hasMany(db.Analysis, { foreignKey: 'userId' });
db.Analysis.belongsTo(db.User, { foreignKey: 'userId' });

module.exports = db;