import os
import re

directory = '/home/cb/AntiGravity/projects/attendance-frontend/src'

replacements = {
    'salmon-DEFAULT': 'nes-blue',
    'salmon-50': 'nes-light',
    'salmon-100': 'nes-light',
    'salmon-600': 'nes-blue',
    'salmon-700': 'nes-blue',
    'salmon-950': 'nes-dark',
    'salmon-400': 'nes-red',
    'text-salmon': 'text-nes-blue',
    'bg-salmon': 'bg-nes-blue',
    'border-salmon': 'border-nes-blue',
    'ring-salmon': 'ring-nes-blue',
    'shadow-salmon': 'shadow-nes-blue',
}

for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith('.tsx') or file.endswith('.ts'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r') as f:
                content = f.read()
            
            new_content = content
            for old, new in replacements.items():
                new_content = new_content.replace(old, new)
            
            if new_content != content:
                with open(filepath, 'w') as f:
                    f.write(new_content)

print("Done replacing colors.")
