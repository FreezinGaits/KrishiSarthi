
with open('run.py', 'rb') as f:
    content = f.read()

# Replace unicode emojis (binary replacement)
# Warning: \xe2\x9a\xa0\xef\xb8\x8f -> WARNING:
content = content.replace(b'\\xe2\\x9a\\xa0\\xef\\xb8\\x8f', b'WARNING:')
# Check mark \xe2\x9c\x85 -> OK
content = content.replace(b'\\xe2\\x9c\\x85', b'')
# Cross mark \xe2\x9d\x8c -> ERROR
content = content.replace(b'\\xe2\\x9d\\x8c', b'')
# Arrow \xe2\x86\x92 -> ->
content = content.replace(b'\\xe2\\x86\\x92', b'->')

with open('run.py', 'wb') as f:
    f.write(content)
print('Patched run.py')

