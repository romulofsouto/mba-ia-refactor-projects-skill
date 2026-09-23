const userModel = require('../models/userModel');

async function deleteUser(req, res) {
    const userId = Number(req.params.id);
    if (!Number.isInteger(userId)) return res.status(400).send('Bad Request');

    const db = req.app.locals.db;
    await db.transaction((tx) => userModel.deleteWithDependents(tx, userId));
    res.send('Usuário deletado.');
}

module.exports = { deleteUser };
