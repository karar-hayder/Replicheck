// utils/helpers.js
// Usage: node helpers.js <path-to-file.js/ts/tsx> [more paths...]
//
// Prints {"<path>": [ {name, complexity, lineno, endline}, ... ], ...}.
// A path whose value is null could not be analysed; the rest of the batch
// still succeeds, so one bad file never costs its batch-mates their results.

const fs = require('fs');
const escomplex = require('typhonjs-escomplex');

const filePaths = process.argv.slice(2);

if (filePaths.length === 0) {
    console.error('Usage: node helpers.js <path-to-js/ts/tsx-file> [more paths...]');
    process.exit(1);
}

const output = {};

for (const filePath of filePaths) {
    try {
        const code = fs.readFileSync(filePath, 'utf-8');
        const result = escomplex.analyzeModule(code);
        const methods = (result && result.methods) || [];
        output[filePath] = methods.map(fn => ({
            name: fn.name,
            complexity: fn.cyclomatic,
            lineno: fn.lineStart,
            endline: fn.lineEnd,
        }));
    } catch (err) {
        // Reported per file on stderr; the batch carries on.
        console.error(`Error analyzing ${filePath}: ${err.message}`);
        output[filePath] = null;
    }
}

console.log(JSON.stringify(output));
