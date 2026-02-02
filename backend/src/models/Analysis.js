const { DataTypes } = require('sequelize');

module.exports = (sequelize) => {
  const Analysis = sequelize.define('Analysis', {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true
    },
    repoUrl: {
      type: DataTypes.STRING,
      allowNull: false
    },
    status: {
      type: DataTypes.ENUM('pending', 'processing', 'completed', 'failed'),
      defaultValue: 'pending'
    },
    language: {
      type: DataTypes.STRING
    },
    score: {
      type: DataTypes.INTEGER
    },
    issues: {
      type: DataTypes.JSONB,
      defaultValue: []
    },
    recommendations: {
      type: DataTypes.JSONB,
      defaultValue: []
    }
  });

  return Analysis;
};