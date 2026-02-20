import sys
sys.path.insert(0, 'backend')

from app.languages.javascript_fixer import JavaScriptFixer
from app.models import ErrorInfo, ErrorType
import os

# Create test file with missing imports
test_file = 'backend/workspace/test_missing_import.jsx'
os.makedirs(os.path.dirname(test_file), exist_ok=True)

with open(test_file, 'w') as f:
    f.write("""import { useNavigate } from "react-router-dom";

function Test() {
    const [count, setCount] = useState(0);
    return <div>{count}</div>;
}
""")

# Create error for missing useState
error = ErrorInfo(
    file=test_file,
    line=4,
    type=ErrorType.LOGIC,
    message="'useState' is not defined (no-undef)"
)

fixer = JavaScriptFixer()
print(f"Testing fix for: {error.message}")
print(f"File: {error.file}:{error.line}\n")
print("Before fix:")
with open(test_file, 'r') as f:
    print(f.read())

result = fixer.fix_error(error)

print(f'\n{"="*50}')
print(f'Fix successful: {result}')
print(f'{"="*50}\n')

# Show the fixed content
print('After fix:')
with open(test_file, 'r') as f:
    print(f.read())

# Cleanup
os.remove(test_file)
