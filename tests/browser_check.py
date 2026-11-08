"""Run deterministic browser interactions; launch fixture_server and frontend first."""
import re
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

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
        page.get_by_role('heading', name='Pagewise', exact=True).wait_for()
        assert page.get_by_role('tab').first.inner_text() == 'Upload a PDF'
        assert page.get_by_role('tab', name='Upload a PDF').get_attribute('aria-selected') == 'true'
        assert 'General documents' in page.locator('[role=tabpanel]:visible').get_by_test_id('stSelectbox').first.inner_text()
        assert page.get_by_test_id('stCaptionContainer').first.evaluate("el => getComputedStyle(el).opacity") == '1'
        page.get_by_role('tab', name='Ask questions').click()
        page.get_by_role('button', name='Get answer').click()
        page.get_by_text('Enter a question about your documents.', exact=True).wait_for()
        page.get_by_role('tab', name='Upload a PDF').click()
        page.get_by_role('button', name='Upload PDF', exact=True).click()
        page.get_by_text('Choose a PDF and enter a document title.', exact=True).wait_for()
        with page.expect_response(lambda response: '/upload_file/' in response.url and response.request.method == 'PUT') as upload:
            page.locator('input[type=file]').set_input_files({'name': 'fixture.pdf', 'mimeType': 'application/pdf', 'buffer': pdf_bytes()})
        assert upload.value.ok
        page.get_by_role('textbox', name='Document title', exact=True).fill('Deterministic test paper')
        page.get_by_role('combobox').first.click()
        page.get_by_role('option', name='Security', exact=True).click()
        page.get_by_role('button', name='Upload PDF', exact=True).click()
        page.get_by_text(re.compile('Ready to use:')).wait_for()
        page.get_by_role('tab', name='Ask questions').click()
        assert 'Security' in page.locator('[role=tabpanel]:visible').get_by_test_id('stSelectbox').filter(has_text='Search category').inner_text()
        page.get_by_text('Question language & starters', exact=True).click()
        page.get_by_role('button', name='List the main steps').click()
        expect(page.get_by_role('textbox', name='Your question')).to_have_value(re.compile('.*main steps.*'))
        page.get_by_text('Question language & starters', exact=True).click()
        page.get_by_role('textbox', name='Your question').fill('What does the test paper compare?')
        # Verify keyboard submission and a persistent answer.
        page.get_by_role('button', name='Get answer').focus()
        page.keyboard.press('Enter')
        page.get_by_text(re.compile('This is a test fixture, not a live model answer.')).wait_for()
        page.get_by_role('heading', name='Source documents').wait_for()
        page.get_by_role('textbox', name='Your question').fill('An unsubmitted draft')
        with page.expect_download() as saved:
            page.get_by_role('button', name='Download answer').click()
        exported = Path(saved.value.path()).read_text(encoding='utf-8')
        assert saved.value.suggested_filename == 'pagewise-answer.md'
        assert 'What does the test paper compare?' in exported
        assert 'An unsubmitted draft' not in exported
        assert 'Security' in exported and 'Deterministic test paper' in exported
        assert 'not a live model answer' in exported
        page.get_by_role('textbox', name='Your question').fill('What evidence supports this method?')
        page.get_by_role('button', name='Get answer').click()
        page.get_by_text('Question: What evidence supports this method? | Category: Security', exact=True).wait_for()
        page.get_by_text('Recent questions in this session', exact=True).click()
        page.get_by_role('combobox').last.click()
        page.get_by_role('option', name=re.compile('What does the test paper compare')).click()
        page.get_by_role('button', name='Show saved answer').click()
        page.get_by_text('Question: What does the test paper compare? | Category: Security', exact=True).wait_for()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), name
        page.evaluate("document.querySelectorAll('*').forEach(el => { if (el.scrollTop) el.scrollTop = 0; })")
        page.screenshot(path=str(OUT / f'{name}.png'), full_page=True)
        page.get_by_role('button', name='Clear session history').click()
        expect(page.get_by_role('textbox', name='Your question')).to_have_value('')
        assert page.get_by_role('heading', name='Answer', exact=True).count() == 0
        print(f'{name}: upload, starter, keyboard submission, download, saved-answer restore and clear passed; no page overflow')
        page.close()
    browser.close()
