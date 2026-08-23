"""
Regression tests for the teacher PDF export (api/pdf_export.py).

This is the first test module in the project and needs WeasyPrint + pypdf,
which are only installed on the VPS container (no local Docker/pip/venv in
the usual dev environment) — run it there:

    docker exec be-web-1 python manage.py test api.tests

Covers the two things that broke silently in the same feature area and were
only caught by eye, not by any automated check: worksheets overflowing past
the 2-per-A4 cut line, and the compact-row column layout collapsing to one
item per line. Assertions read the actual generated PDF (via pypdf), not
just HTTP status, so a future change that produces a "successful" but wrong
PDF still fails the test.
"""
import json
import re
from collections import Counter
from io import BytesIO

from django.template.loader import render_to_string
from django.test import TestCase
from pypdf import PdfReader

from .models import Answer, Example, Teacher


class PdfExportTestCase(TestCase):
    def setUp(self):
        self.teacher = Teacher.objects.create(
            email='pdftest@example.com', password='x',
            first_name='Test', last_name='Teacher',
        )
        self.examples = []
        for i in range(1, 21):
            ex = Example.objects.create(example=f'{i} + ? = 10', input_type='INLINE')
            Answer.objects.create(example=ex, answer=str(10 - i))
            self.examples.append(ex)
        self.word_example = Example.objects.create(
            example='Ratchet potrebuje 50 jednotiek kovu na opravu.',
            input_type='WORD',
        )
        Answer.objects.create(example=self.word_example, answer='10')
        self.frac_example = Example.objects.create(
            example=r'\frac{1}{3} + \frac{1}{2}', input_type='FRAC',
        )
        Answer.objects.create(example=self.frac_example, answer='5/6')

    def _items(self, examples, **overrides):
        return [{'example_id': ex.id, 'points': 1, **overrides} for ex in examples]

    def _post(self, payload, debug_html=False):
        url = '/api/teacher/print/test/' + ('?debug=html' if debug_html else '')
        body = {'teacher_id': self.teacher.id, **payload}
        return self.client.post(url, data=json.dumps(body), content_type='application/json')

    def _pdf(self, response):
        self.assertEqual(response.status_code, 200, response.content[:500])
        self.assertEqual(response['Content-Type'], 'application/pdf')
        return PdfReader(BytesIO(response.content))

    # ---- per_page == 1 --------------------------------------------------

    def test_per_page_1_single_page(self):
        response = self._post({
            'title': 'P1 basic', 'per_page': '1', 'groups': 1, 'columns': 2,
            'items': self._items(self.examples[:4]),
        })
        reader = self._pdf(response)
        self.assertEqual(len(reader.pages), 1)
        text = reader.pages[0].extract_text()
        self.assertIn('P1 basic', text)
        self.assertIn('1 + ? = 10', text)

    def test_per_page_1_multi_page_keeps_every_item(self):
        response = self._post({
            'title': 'P1 multipage', 'per_page': '1', 'groups': 1, 'columns': 1,
            'items': self._items(self.examples),  # 20 items, 1/row -> forces >1 page
        })
        reader = self._pdf(response)
        self.assertGreater(len(reader.pages), 1)
        full_text = '\n'.join(p.extract_text() for p in reader.pages)
        numbers = Counter(int(n) for n in re.findall(r'(?<!\d)(\d+)\.\s*\(', full_text))
        for i in range(1, 21):
            self.assertEqual(numbers[i], 1, f'item {i} appeared {numbers[i]} times, expected 1')

    # ---- per_page == 2 imposition ---------------------------------------

    def test_per_page_2_basic_pairing_with_cover_and_key(self):
        response = self._post({
            'title': 'P2 pairing', 'per_page': '2', 'groups': 2, 'columns': 2,
            'cover_page': True, 'answer_key': True,
            'items': self._items(self.examples[:6]),
        })
        reader = self._pdf(response)
        # cover + 1 shared A4 (A top, B bottom) + answer key == 3 pages
        self.assertEqual(len(reader.pages), 3)
        self.assertIn('P2 pairing', reader.pages[0].extract_text())
        sheet_text = reader.pages[1].extract_text()
        self.assertIn('A', sheet_text)
        self.assertIn('B', sheet_text)
        self.assertIn('Kľúč', reader.pages[2].extract_text())

    def test_per_page_2_columns_render_side_by_side(self):
        """Regression guard for the compact-row column layout bug: two
        items sharing a compact row must land on the same visual line, not
        stack one-per-line — which is what a broken flex/table-cell layout
        silently degraded to, and was invisible until the live preview
        started rendering the real PDF instead of a browser approximation."""
        response = self._post({
            'title': 'Columns', 'per_page': '2', 'groups': 1, 'columns': 2,
            'items': self._items(self.examples[:4]),
        })
        reader = self._pdf(response)
        layout_text = reader.pages[0].extract_text(extraction_mode='layout')
        same_line = [ln for ln in layout_text.split('\n') if '1.' in ln and '2.' in ln]
        self.assertTrue(same_line, f'items 1 and 2 are not on the same line:\n{layout_text}')

    def test_per_page_2_never_overflows_continues_on_next_half_page(self):
        """The core overflow fix: content that doesn't fit a half-page must
        continue onto the next physical half-page rather than overflow past
        the cut line, and no item may be lost or duplicated in the process."""
        many = self.examples * 4  # 80 items — several half-pages worth
        response = self._post({
            'title': 'Overflow guard', 'per_page': '2', 'groups': 1, 'columns': 2,
            'items': self._items(many),
        })
        reader = self._pdf(response)
        self.assertGreater(len(reader.pages), 1)
        full_text = '\n'.join(p.extract_text() for p in reader.pages)
        numbers = Counter(int(n) for n in re.findall(r'(?<!\d)(\d+)\.\s*\(', full_text))
        for i in range(1, len(many) + 1):
            # groups == 1 duplicates the single sheet as both halves of
            # every shared page, so each item legitimately appears twice.
            self.assertEqual(numbers[i], 2, f'item {i} appeared {numbers[i]} times, expected 2')
        self.assertIn('pokračovanie', full_text)

    def test_per_page_2_odd_group_count_duplicates_last_sheet(self):
        response = self._post({
            'title': 'Odd groups', 'per_page': '2', 'groups': 3, 'columns': 2,
            'items': self._items(self.examples[:4]),
        })
        reader = self._pdf(response)
        self.assertEqual(len(reader.pages), 2)  # (A,B) shared page, (C,C) shared page
        page1, page2 = (p.extract_text() for p in reader.pages)
        self.assertIn('A', page1)
        self.assertIn('B', page1)
        self.assertEqual(page2.count('C'), 2)

    def test_wide_items_render_with_answer_space(self):
        response = self._post({
            'title': 'Wide items', 'per_page': '2', 'groups': 1, 'columns': 2,
            'items': self._items([self.word_example, self.frac_example]),
        })
        reader = self._pdf(response)
        text = reader.pages[0].extract_text()
        self.assertIn('Ratchet', text)
        self.assertIn('1', text)
        self.assertIn('3', text)  # numerator/denominator of the fraction

    def test_debug_html_returns_html_for_both_modes(self):
        for per_page in ('1', '2'):
            response = self._post({
                'title': 'Debug', 'per_page': per_page, 'groups': 1,
                'items': self._items(self.examples[:2]),
            }, debug_html=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn('text/html', response['Content-Type'])
            self.assertIn(b'<html', response.content[:200])

    def test_shared_style_has_no_leaked_template_comment(self):
        """Regression guard: a multi-line {# #} Django comment isn't valid
        (Django comments are single-line only) and leaks through as literal
        text into the CSS — which is exactly what silently broke both the
        compact-row layout and the DejaVu Sans font-family rule right after
        it, until someone happened to look at a real rendered PDF."""
        css = render_to_string('pdf/_shared_style.html', {'row_gap_mm': 2})
        self.assertNotIn('{#', css)
        self.assertNotIn('#}', css)
        self.assertIn("font-family: 'DejaVu Sans'", css)
