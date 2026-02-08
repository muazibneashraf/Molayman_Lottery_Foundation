with open('app/templates/main/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove floating orbs section
old_orbs = '''      <!-- Floating orbs -->
      <div class="absolute top-20 left-[10%] w-72 h-72 bg-gradient-to-br from-primary/20 to-secondary/20 rounded-full blur-3xl animate-pulse"></div>
      <div class="absolute bottom-20 right-[10%] w-96 h-96 bg-gradient-to-br from-yellow-200/20 to-pink-200/20 rounded-full blur-3xl animate-pulse" style="animation-delay:2s"></div>
    '''

new_orbs = '    '

content = content.replace(old_orbs, new_orbs)

# Replace animated gradient text with solid color
content = content.replace('text-gradient-animated', 'text-primary')

with open('app/templates/main/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Removed orbs and animation from index.html")
