// utils/helpers.js
// Usage: node helpers.js <path-to-js-file>
const fs = require('fs');
const escomplex = require('typhonjs-escomplex');

if (process.argv.length < 3) {
    console.error('Usage: node helpers.js <path-to-js-file>');
    process.exit(1);
}

const filePath = process.argv[2];
let code;
try {
    code = fs.readFileSync(filePath, 'utf-8');
} catch (err) {
    console.error('Error reading file:', err.message);
    process.exit(1);
}

const result = escomplex.analyzeModule(code);
const methods = (result && result.methods) || [];
const output = methods.map(fn => ({
    name: fn.name,
    complexity: fn.cyclomatic,
    lineno: fn.lineStart,
    endline: fn.lineEnd,
}));
console.log(JSON.stringify(output)); 