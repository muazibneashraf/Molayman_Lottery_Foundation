import re

# Fix index.html
with open('app/templates/main/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove floating orbs
content = re.sub(
    r'\n\s*<!-- Floating orbs -->.*?animation-delay:2s\"></div>',
    '',
    content,
    flags=re.DOTALL
)

# Replace animated gradient text with solid color
content = content.replace('text-gradient-animated', 'text-primary')

with open('app/templates/main/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Removed orbs and animation from index.html")
