# Fix script - more aggressive
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Split into lines
lines = content.split('\n')
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Look for the problematic pattern
    if '@app.route' in line and 'mark-read' in line:
        # Check if this is a valid route or orphan
        if i+1 < len(lines):
            next_line = lines[i+1]
            if not ('@login_required' in next_line or 'def ' in next_line):
                # This is orphan code - skip it and all following lines that don't start with @
                while i < len(lines):
                    curr = lines[i]
                    if curr.strip().startswith('@') or curr.strip().startswith('def '):
                        break
                    i += 1
                continue
    new_lines.append(line)
    i += 1

# Write back
with open('app.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print("Done!")
