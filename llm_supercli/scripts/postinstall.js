const { execSync } = require('child_process');
const path = require('path');

const pipCmd = process.platform === 'win32' ? 'pip' : 'pip3';

console.log('Installing Python dependencies...');

try {
  // Install from pyproject.toml in package directory
  const pkgDir = path.join(__dirname, '..');
  execSync(`${pipCmd} install "${pkgDir}"`, { stdio: 'inherit' });
  console.log('✅ llm-supercli installed successfully!');
  console.log('Run "llm" or "llm-supercli" to start.');
} catch (err) {
  // Fallback: try installing dependencies directly
  console.log('Trying fallback installation...');
  try {
    execSync(`${pipCmd} install rich httpx click prompt_toolkit pyfiglet`, { stdio: 'inherit' });
    console.log('✅ Dependencies installed. Run "llm" or "llm-supercli" to start.');
  } catch (err2) {
    console.error('❌ Failed to install Python dependencies.');
    console.error('Please run manually: pip install rich httpx click prompt_toolkit pyfiglet');
    process.exit(1);
  }
}
