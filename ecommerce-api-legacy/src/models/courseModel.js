async function findActiveById(db, courseId) {
    return db.get('SELECT id, title, price FROM courses WHERE id = ? AND active = 1', [courseId]);
}

// One row per (course, enrollment); courses without enrollments come back with null enrollment columns.
async function findEnrollmentsWithPayments(db) {
    return db.all(`
        SELECT c.id AS course_id, c.title, e.id AS enrollment_id,
               u.name AS student_name, p.amount, p.status
        FROM courses c
        LEFT JOIN enrollments e ON e.course_id = c.id
        LEFT JOIN users u ON u.id = e.user_id
        LEFT JOIN payments p ON p.enrollment_id = e.id
        ORDER BY c.id, e.id
    `);
}

module.exports = { findActiveById, findEnrollmentsWithPayments };
