const { execSync } = require('child_process');
const path = require('path');

const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
const pipCmd = process.platform === 'win32' ? 'pip' : 'pip3';

console.log('Installing Python dependencies...');

try {
  execSync(`${pipCmd} install -e "${path.join(__dirname, '..')}"`, { stdio: 'inherit' });
  console.log('✅ llm-supercli installed successfully!');
  console.log('Run "llm" or "llm-supercli" to start.');
} catch (err) {
  console.error('❌ Failed to install Python dependencies.');
  console.error('Make sure Python 3.10+ and pip are installed.');
  process.exit(1);
}
