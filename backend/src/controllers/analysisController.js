const { Analysis, Repository, Issue, Metric } = require('../models');
const analysisService = require('../services/analysisService');
const queueService = require('../services/queueService');
const logger = require('../utils/logger');

/**
 * Start a new code analysis
 */
exports.startAnalysis = async (req, res, next) => {
  try {
    const { repositoryId, branch, commitSha } = req.body;
    const userId = req.user.id;

    // Verify repository ownership
    const repository = await Repository.findOne({
      where: { id: repositoryId, userId }
    });

    if (!repository) {
      return res.status(404).json({
        success: false,
        message: 'Repository not found'
      });
    }

    // Check for existing pending/processing analysis
    const existingAnalysis = await Analysis.findOne({
      where: {
        repositoryId,
        status: ['pending', 'processing']
      }
    });

    if (existingAnalysis) {
      return res.status(409).json({
        success: false,
        message: 'An analysis is already in progress for this repository',
        analysisId: existingAnalysis.id
      });
    }

    // Create new analysis record
    const analysis = await Analysis.create({
      repositoryId,
      branch: branch || repository.defaultBranch,
      commitSha,
      status: 'pending'
    });

    // Queue the analysis job
    const job = await queueService.addAnalysisJob({
      analysisId: analysis.id,
      repositoryId: repository.id,
      repositoryUrl: repository.cloneUrl,
      branch: analysis.branch,
      commitSha: analysis.commitSha
    });

    logger.info(`Analysis queued: ${analysis.id}, Job ID: ${job.id}`);

    res.status(201).json({
      success: true,
      message: 'Analysis started successfully',
      data: {
        analysisId: analysis.id,
        jobId: job.id,
        status: 'pending'
      }
    });
  } catch (error) {
    logger.error('Error starting analysis:', error);
    next(error);
  }
};

/**
 * Get analysis by ID
 */
exports.getAnalysis = async (req, res, next) => {
  try {
    const { id } = req.params;
    const userId = req.user.id;

    const analysis = await Analysis.findOne({
      where: { id },
      include: [
        {
          model: Repository,
          where: { userId },
          attributes: ['id', 'name', 'fullName', 'url', 'language']
        },
        {
          model: Issue,
          attributes: ['id', 'severity', 'category', 'title', 'filePath', 'lineNumber']
        },
        {
          model: Metric,
          attributes: ['id', 'metricType', 'value', 'filePath']
        }
      ]
    });

    if (!analysis) {
      return res.status(404).json({
        success: false,
        message: 'Analysis not found'
      });
    }

    // Calculate summary statistics
    const issuesBySeverity = analysis.Issues.reduce((acc, issue) => {
      acc[issue.severity] = (acc[issue.severity] || 0) + 1;
      return acc;
    }, {});

    const issuesByCategory = analysis.Issues.reduce((acc, issue) => {
      acc[issue.category] = (acc[issue.category] || 0) + 1;
      return acc;
    }, {});

    res.json({
      success: true,
      data: {
        ...analysis.toJSON(),
        summary: {
          issuesBySeverity,
          issuesByCategory,
          totalIssues: analysis.Issues.length,
          totalMetrics: analysis.Metrics.length
        }
      }
    });
  } catch (error) {
    logger.error('Error fetching analysis:', error);
    next(error);
  }
};

/**
 * Get all analyses for a repository
 */
exports.getRepositoryAnalyses = async (req, res, next) => {
  try {
    const { repositoryId } = req.params;
    const userId = req.user.id;
    const { page = 1, limit = 10 } = req.query;

    // Verify repository ownership
    const repository = await Repository.findOne({
      where: { id: repositoryId, userId }
    });

    if (!repository) {
      return res.status(404).json({
        success: false,
        message: 'Repository not found'
      });
    }

    const offset = (page - 1) * limit;

    const { count, rows: analyses } = await Analysis.findAndCountAll({
      where: { repositoryId },
      limit: parseInt(limit),
      offset: parseInt(offset),
      order: [['createdAt', 'DESC']],
      attributes: [
        'id',
        'commitSha',
        'branch',
        'status',
        'qualityScore',
        'maintainabilityIndex',
        'complexityScore',
        'securityRating',
        'issuesFound',
        'filesAnalyzed',
        'createdAt',
        'completedAt'
      ]
    });

    res.json({
      success: true,
      data: {
        analyses,
        pagination: {
          total: count,
          page: parseInt(page),
          limit: parseInt(limit),
          totalPages: Math.ceil(count / limit)
        }
      }
    });
  } catch (error) {
    logger.error('Error fetching repository analyses:', error);
    next(error);
  }
};

/**
 * Get analysis issues with filtering
 */
exports.getAnalysisIssues = async (req, res, next) => {
  try {
    const { id } = req.params;
    const { severity, category, page = 1, limit = 50 } = req.query;
    const userId = req.user.id;

    // Verify analysis ownership
    const analysis = await Analysis.findOne({
      where: { id },
      include: [{
        model: Repository,
        where: { userId },
        attributes: ['id']
      }]
    });

    if (!analysis) {
      return res.status(404).json({
        success: false,
        message: 'Analysis not found'
      });
    }

    const where = { analysisId: id };
    if (severity) where.severity = severity;
    if (category) where.category = category;

    const offset = (page - 1) * limit;

    const { count, rows: issues } = await Issue.findAndCountAll({
      where,
      limit: parseInt(limit),
      offset: parseInt(offset),
      order: [
        ['severity', 'ASC'], // Critical first
        ['lineNumber', 'ASC']
      ]
    });

    res.json({
      success: true,
      data: {
        issues,
        pagination: {
          total: count,
          page: parseInt(page),
          limit: parseInt(limit),
          totalPages: Math.ceil(count / limit)
        }
      }
    });
  } catch (error) {
    logger.error('Error fetching analysis issues:', error);
    next(error);
  }
};

/**
 * Get analysis metrics
 */
exports.getAnalysisMetrics = async (req, res, next) => {
  try {
    const { id } = req.params;
    const { metricType, filePath } = req.query;
    const userId = req.user.id;

    // Verify analysis ownership
    const analysis = await Analysis.findOne({
      where: { id },
      include: [{
        model: Repository,
        where: { userId },
        attributes: ['id']
      }]
    });

    if (!analysis) {
      return res.status(404).json({
        success: false,
        message: 'Analysis not found'
      });
    }

    const where = { analysisId: id };
    if (metricType) where.metricType = metricType;
    if (filePath) where.filePath = filePath;

    const metrics = await Metric.findAll({
      where,
      order: [['value', 'DESC']]
    });

    // Group metrics by type
    const groupedMetrics = metrics.reduce((acc, metric) => {
      if (!acc[metric.metricType]) {
        acc[metric.metricType] = [];
      }
      acc[metric.metricType].push(metric);
      return acc;
    }, {});

    res.json({
      success: true,
      data: {
        metrics,
        grouped: groupedMetrics
      }
    });
  } catch (error) {
    logger.error('Error fetching analysis metrics:', error);
    next(error);
  }
};

/**
 * Cancel an ongoing analysis
 */
exports.cancelAnalysis = async (req, res, next) => {
  try {
    const { id } = req.params;
    const userId = req.user.id;

    const analysis = await Analysis.findOne({
      where: { id },
      include: [{
        model: Repository,
        where: { userId },
        attributes: ['id']
      }]
    });

    if (!analysis) {
      return res.status(404).json({
        success: false,
        message: 'Analysis not found'
      });
    }

    if (!['pending', 'processing'].includes(analysis.status)) {
      return res.status(400).json({
        success: false,
        message: 'Cannot cancel analysis in current status'
      });
    }

    // Cancel the job in queue
    await queueService.cancelAnalysisJob(analysis.id);

    // Update analysis status
    await analysis.update({ status: 'cancelled' });

    logger.info(`Analysis cancelled: ${analysis.id}`);

    res.json({
      success: true,
      message: 'Analysis cancelled successfully'
    });
  } catch (error) {
    logger.error('Error cancelling analysis:', error);
    next(error);
  }
};

/**
 * Get analysis statistics
 */
exports.getAnalysisStats = async (req, res, next) => {
  try {
    const userId = req.user.id;

    const stats = await analysisService.getUserAnalysisStats(userId);

    res.json({
      success: true,
      data: stats
    });
  } catch (error) {
    logger.error('Error fetching analysis stats:', error);
    next(error);
  }
};