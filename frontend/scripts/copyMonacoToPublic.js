const fs = require('fs-extra');
const path = require('path');

const sourcePath = path.join(__dirname, '../node_modules/monaco-editor/min/vs');
const targetPath = path.join(__dirname, '../public/monaco-assets/vs');

if (!fs.existsSync(sourcePath)) {
  console.error(`Error: Source directory ${sourcePath} does not exist.`);
  console.error('Please run: npm install monaco-editor');
  process.exit(1);
}

fs.ensureDirSync(targetPath);

try {
  fs.copySync(sourcePath, targetPath, {
    overwrite: true,
    errorOnExist: false,
  });
  console.log(`Success: Copied Monaco Editor from ${sourcePath} to ${targetPath}`);
} catch (error) {
  console.error(`Error: ${error.message}`);
  process.exit(1);
}
