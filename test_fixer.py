import sys
sys.path.insert(0, 'backend')

from app.languages.javascript_fixer import JavaScriptFixer
from app.models import ErrorInfo, ErrorType
import os

# Create test file
test_file = 'backend/workspace/test_fix.jsx'
os.makedirs(os.path.dirname(test_file), exist_ok=True)

with open(test_file, 'w') as f:
    f.write("""import React from "react";
import { useState } from "react";

function Test() {
    const [count, setCount] = useState(0);
    return <div>{count}</div>;
}
""")

# Create error for 'React' unused
error = ErrorInfo(
    file=test_file,
    line=1,
    type=ErrorType.LOGIC,
    message="'React' is defined but never used (no-unused-vars)"
)

fixer = JavaScriptFixer()
print(f"Testing fix for: {error.message}")
print(f"File: {error.file}:{error.line}\n")

result = fixer.fix_error(error)

print(f'\nFix successful: {result}')

# Show the fixed content
print('\nFixed content:')
with open(test_file, 'r') as f:
    print(f.read())

# Cleanup
os.remove(test_file)
