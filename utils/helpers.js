// utils/helpers.js
// Usage: node helpers.js <path-to-file.js/ts/tsx>

const fs = require('fs');
const path = require('path');
const escomplex = require('typhonjs-escomplex');
const babel = require('@babel/parser');

if (process.argv.length < 3) {
    console.error('Usage: node helpers.js <path-to-js/ts/tsx-file>');
    process.exit(1);
}

const filePath = process.argv[2];
const ext = path.extname(filePath).toLowerCase();

let code;
try {
    code = fs.readFileSync(filePath, 'utf-8');
} catch (err) {
    console.error('Error reading file:', err.message);
    process.exit(1);
}

//// USE LATER FOR AST AND REFACTORING FEATURES
// let ast;
// try {
//     ast = babel.parse(code, {
//         sourceType: 'module',
//         plugins: [
//             'jsx',
//             ...(ext === '.ts' || ext === '.tsx' ? ['typescript'] : [])
//         ]
//     });
//     console.info("ast")
//     console.info(ast)
// } catch (err) {
//     console.error('Error parsing code:', err.message);
//     process.exit(1);
// }

let result;
try {
    result = escomplex.analyzeModule(code);
} catch (err) {
    console.error('Error analyzing complexity:', err.message);
    process.exit(1);
}

const methods = (result && result.methods) || [];
const output = methods.map(fn => ({
    name: fn.name,
    complexity: fn.cyclomatic,
    lineno: fn.lineStart,
    endline: fn.lineEnd,
}));

console.log(JSON.stringify(output));
