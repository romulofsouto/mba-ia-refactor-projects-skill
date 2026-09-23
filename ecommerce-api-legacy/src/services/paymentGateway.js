const PAID = 'PAID';
const DENIED = 'DENIED';

// Simulated gateway: Visa cards (prefix 4) are approved, everything else is denied.
function charge(cardNumber) {
    return cardNumber.startsWith('4') ? PAID : DENIED;
}

module.exports = { charge, PAID, DENIED };
