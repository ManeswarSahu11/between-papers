"""Run deterministic browser interactions; launch fixture_server and frontend first."""
import re
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'images'
OUT.mkdir(exist_ok=True)

def pdf_bytes():
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    from io import BytesIO
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 50 700 Td (This deterministic test paper compares retrieved passages.) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    result = BytesIO()
    writer.write(result)
    return result.getvalue()

with sync_playwright() as p:
    browser = p.chromium.launch()
    for name, width, height in [('phone', 390, 844), ('tablet', 768, 1024), ('desktop', 1440, 1500)]:
        page = browser.new_page(viewport={'width': width, 'height': height})
        page.goto(os.getenv('BROWSER_TEST_URL', 'http://127.0.0.1:18502'))
        page.get_by_role('heading', name='Between Papers', exact=True).wait_for()
        page.get_by_role('tab', name='Ask your papers').click()
        page.get_by_role('button', name='Find an answer').click()
        page.get_by_text('Enter a question to search your papers.', exact=True).wait_for()
        page.get_by_role('tab', name='Add a paper').click()
        page.get_by_role('button', name='Index paper', exact=True).click()
        page.get_by_text('Choose a PDF and enter its title.', exact=True).wait_for()
        page.locator('input[type=file]').set_input_files({'name': 'fixture.pdf', 'mimeType': 'application/pdf', 'buffer': pdf_bytes()})
        page.get_by_role('textbox', name='Paper title', exact=True).fill('Deterministic test paper')
        page.get_by_role('combobox').first.click()
        page.get_by_role('option', name='Security', exact=True).click()
        page.get_by_role('button', name='Index paper', exact=True).click()
        page.get_by_text(re.compile('Paper indexed:')).wait_for()
        page.get_by_role('tab', name='Ask your papers').click()
        assert 'Security' in page.locator('[role=tabpanel]:visible').get_by_test_id('stSelectbox').first.inner_text()
        page.get_by_role('textbox', name='Your question').fill('What does the test paper compare?')
        # Verify keyboard submission and a persistent answer.
        page.get_by_role('button', name='Find an answer').focus()
        page.keyboard.press('Enter')
        page.get_by_text(re.compile('This is a test fixture, not a live model answer.')).wait_for()
        page.get_by_role('heading', name='Retrieved papers').wait_for()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), name
        page.evaluate("document.querySelectorAll('*').forEach(el => { if (el.scrollTop) el.scrollTop = 0; })")
        page.screenshot(path=str(OUT / f'{name}.png'), full_page=True)
        print(f'{name}: upload, validation, keyboard submission, answer and sources passed; no page overflow')
        page.close()
    browser.close()
