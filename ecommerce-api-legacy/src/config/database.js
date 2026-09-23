const sqlite3 = require('sqlite3');
const { hashPassword } = require('../services/passwordHasher');

// Promise wrapper over the callback-style sqlite3 driver.
function createDatabase(filename) {
    const conn = new sqlite3.Database(filename);
    let txQueue = Promise.resolve();

    const db = {
        run(sql, params = []) {
            return new Promise((resolve, reject) => {
                conn.run(sql, params, function (err) {
                    if (err) return reject(err);
                    resolve({ lastID: this.lastID, changes: this.changes });
                });
            });
        },
        get(sql, params = []) {
            return new Promise((resolve, reject) => {
                conn.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
            });
        },
        all(sql, params = []) {
            return new Promise((resolve, reject) => {
                conn.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
            });
        },
        // Transactions are serialized: sqlite3 shares a single connection across requests.
        transaction(work) {
            const result = txQueue.then(async () => {
                await db.run('BEGIN');
                try {
                    const value = await work(db);
                    await db.run('COMMIT');
                    return value;
                } catch (err) {
                    await db.run('ROLLBACK');
                    throw err;
                }
            });
            txQueue = result.catch(() => {});
            return result;
        },
        close() {
            return new Promise((resolve, reject) => conn.close((err) => (err ? reject(err) : resolve())));
        },
    };
    return db;
}

async function initSchema(db) {
    await db.run('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, pass TEXT)');
    await db.run('CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY, title TEXT, price REAL, active INTEGER)');
    await db.run('CREATE TABLE IF NOT EXISTS enrollments (id INTEGER PRIMARY KEY, user_id INTEGER, course_id INTEGER)');
    await db.run('CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY, enrollment_id INTEGER, amount REAL, status TEXT)');
    await db.run('CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY, action TEXT, created_at DATETIME)');
}

async function seed(db) {
    const { count } = await db.get('SELECT COUNT(*) AS count FROM users');
    if (count > 0) return;

    await db.transaction(async (tx) => {
        await tx.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', ['Leonan', 'leonan@fullcycle.com.br', hashPassword('123')]);
        await tx.run("INSERT INTO courses (title, price, active) VALUES ('Clean Architecture', 997.00, 1), ('Docker', 497.00, 1)");
        await tx.run('INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)');
        await tx.run("INSERT INTO payments (enrollment_id, amount, status) VALUES (1, 997.00, 'PAID')");
    });
}

async function connect(filename) {
    const db = createDatabase(filename);
    await initSchema(db);
    await seed(db);
    return db;
}

module.exports = { connect };
