import re

with open('app/templates/client/games.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove fav-btn buttons (multiline regex)
content = re.sub(r'\s*<button class="fav-btn"[^>]*>.*?</button>\n', '', content, flags=re.DOTALL)

with open('app/templates/client/games.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Removed all 41 fav-btn buttons successfully")
