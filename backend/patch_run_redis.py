
with open('run.py', 'rb') as f:
    content = f.read()

# Replace unicode emojis (binary replacement) for Redis checks
# Hourglass \xe2\x8c\x9b -> (nothing)
content = content.replace(b'\\xe2\\x8c\\x9b', b'')
# Check mark \xe2\x9c\x85 -> OK
content = content.replace(b'\\xe2\\x9c\\x85', b'')
# Warning \xe2\x9a\xa0\xef\xb8\x8f -> WARNING:
content = content.replace(b'\\xe2\\x9a\\xa0\\xef\\xb8\\x8f', b'WARNING:')

with open('run.py', 'wb') as f:
    f.write(content)
print('Patched run.py for Redis emojis')

