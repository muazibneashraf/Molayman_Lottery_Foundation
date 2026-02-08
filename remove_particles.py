import re

with open('app/templates/base.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and remove the particle background function
# Look for the comment and the entire IIFE function
pattern = r'\n\s*// Ambient particle background\n\s*\(function initParticles\(\).*?});\(\);'
content = re.sub(pattern, '', content, flags=re.DOTALL)

with open('app/templates/base.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Removed particle background code")
