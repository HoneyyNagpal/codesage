const express = require('express');
const router = express.Router();
const db = require('../config/database');
const axios = require('axios');

const ANALYZER_URL = process.env.ANALYZER_URL || 'http://localhost:8000';

// Submit new analysis
router.post('/', async (req, res) => {
  try {
    const { repoUrl, language, analyzeSecurity, analyzePerformance } = req.body;

    // Create analysis record
    const analysis = await db.Analysis.create({
      repoUrl,
      language: language || 'auto',
      status: 'pending',
      userId: req.user?.id, // Associate with logged-in user
    });

    // Send to analyzer service
    try {
      const analyzerResponse = await axios.post(`${ANALYZER_URL}/api/v1/analyze`, {
        repo_url: repoUrl,
        language: language || 'auto',
        analyze_security: analyzeSecurity,
        analyze_performance: analyzePerformance,
      });

      const analysisId = analyzerResponse.data.analysis_id;

      await analysis.update({
        status: 'processing',
      });

      // Poll for results after 5 seconds
      setTimeout(async () => {
        try {
          const resultResponse = await axios.get(`${ANALYZER_URL}/api/v1/analyze/${analysisId}`);
          const result = resultResponse.data;

          await db.Analysis.update(
            {
              status: result.status,
              score: result.score,
              issues: result.issues,
              recommendations: [result.summary],
            },
            { where: { id: analysis.id } }
          );
        } catch (error) {
          console.error('Failed to fetch analysis results:', error);
        }
      }, 5000);

      res.status(201).json({
        id: analysis.id,
        status: analysis.status,
        repoUrl: analysis.repoUrl,
        message: 'Analysis started successfully',
      });
    } catch (analyzerError) {
      await analysis.update({ status: 'failed' });
      throw analyzerError;
    }
  } catch (error) {
    console.error('Analysis submission error:', error);
    res.status(500).json({ error: 'Failed to submit analysis' });
  }
});

// Get all analyses
router.get('/', async (req, res) => {
  try {
    const where = req.user ? { userId: req.user.id } : {};
    const analyses = await db.Analysis.findAll({
      where,
      order: [['createdAt', 'DESC']],
    });
    res.json(analyses);
  } catch (error) {
    console.error('Get analyses error:', error);
    res.status(500).json({ error: 'Failed to fetch analyses' });
  }
});

// Get single analysis
router.get('/:id', async (req, res) => {
  try {
    const analysis = await db.Analysis.findByPk(req.params.id);
    if (!analysis) {
      return res.status(404).json({ error: 'Analysis not found' });
    }
    res.json(analysis);
  } catch (error) {
    console.error('Get analysis error:', error);
    res.status(500).json({ error: 'Failed to fetch analysis' });
  }
});

module.exports = router;