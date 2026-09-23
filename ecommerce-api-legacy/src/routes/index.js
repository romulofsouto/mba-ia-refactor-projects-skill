const { Router } = require('express');
const asyncHandler = require('../middlewares/asyncHandler');
const requireAdmin = require('../middlewares/requireAdmin');
const checkoutController = require('../controllers/checkoutController');
const reportController = require('../controllers/reportController');
const userController = require('../controllers/userController');

const router = Router();

router.post('/api/checkout', asyncHandler(checkoutController.checkout));
router.get('/api/admin/financial-report', requireAdmin, asyncHandler(reportController.financialReport));
router.delete('/api/users/:id', requireAdmin, asyncHandler(userController.deleteUser));

module.exports = router;
