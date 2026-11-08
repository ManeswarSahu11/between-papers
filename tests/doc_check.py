"""Check first-party Markdown links and render every first-party Mermaid diagram."""
from pathlib import Path
import re
import requests
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
files = [root / 'README.md', root / 'MAINTAINERS.md', *sorted((root / 'docs').glob('*.md'))]
diagrams = []
for path in files:
    text = path.read_text(encoding='utf-8')
    for target in re.findall(r'\]\(([^)]+)\)', text):
        if target.startswith(('https://', 'http://', '#', 'mailto:')):
            continue
        target = target.split('#')[0]
        assert (path.parent / target).exists(), f'{path}: {target}'
    diagrams.extend(re.findall(r'```mermaid\s*\n(.*?)```', text, re.S))
script = requests.get('https://cdn.jsdelivr.net/npm/mermaid@11.12.2/dist/mermaid.min.js', timeout=90)
script.raise_for_status()
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content('<html><body></body></html>')
    page.add_script_tag(content=script.text)
    for index, diagram in enumerate(diagrams):
        result = page.evaluate('''async ({text, index}) => {
            mermaid.initialize({startOnLoad: false, securityLevel: 'strict'});
            const result = await mermaid.render('diagram' + index, text);
            return result.svg;
        }''', {'text': diagram, 'index': index})
        assert '<svg' in result
    browser.close()
print(f'First-party Markdown links and image references passed; {len(diagrams)} Mermaid diagrams rendered successfully.')
