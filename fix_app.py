# Fix script
import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the broken section around line 2530
# Look for the pattern: return jsonify(notifications) followed by orphan code
lines = content.split('\n')
new_lines = []
skip_mode = False

for i, line in enumerate(lines):
    # Look for the orphan code: @app.route followed by non-def line
    if "@app.route('/api/user/notifications/mark-read'" in line and i+1 < len(lines):
        next_line = lines[i+1]
        # If the next line is NOT @login_required or def, it's orphan
        if '@login_required' not in next_line and 'def ' not in next_line:
            skip_mode = True
            continue
    
    if skip_mode:
        # Skip until we find a line that starts a new valid route
        if line.strip().startswith('@app.route') or (line.strip().startswith('def ') and not line.strip().startswith('def get_user')):
            skip_mode = False
            new_lines.append(line)
        continue
    
    new_lines.append(line)

# Write back
with open('app.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print("Done!")
