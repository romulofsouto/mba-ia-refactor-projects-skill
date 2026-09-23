async function findByEmail(db, email) {
    return db.get('SELECT id, name, email FROM users WHERE email = ?', [email]);
}

async function create(db, { name, email, passwordHash }) {
    const { lastID } = await db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [name, email, passwordHash]);
    return lastID;
}

// Removes the user together with their enrollments and payments.
async function deleteWithDependents(db, userId) {
    await db.run('DELETE FROM payments WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)', [userId]);
    await db.run('DELETE FROM enrollments WHERE user_id = ?', [userId]);
    const { changes } = await db.run('DELETE FROM users WHERE id = ?', [userId]);
    return changes > 0;
}

module.exports = { findByEmail, create, deleteWithDependents };
