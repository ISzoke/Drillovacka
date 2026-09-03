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


class ParentPrintTestCase(TestCase):
    """Regression tests for the parent/student practice sheet (Fáza 2.2).

    The 'hold it to the light' feature only works if page 1 (problems) and
    page 2 (mirrored answers) are each exactly one A4 page with matching row
    positions — so the tests assert page counts and answer content from the
    real rendered PDF, not just HTTP status."""

    def setUp(self):
        self.examples = []
        for i in range(1, 21):
            ex = Example.objects.create(example=f'{i} + 1', input_type='INLINE')
            Answer.objects.create(example=ex, answer=str(i + 1))
            self.examples.append(ex)

    def _post(self, payload, debug_html=False):
        url = '/api/print/parent/' + ('?debug=html' if debug_html else '')
        return self.client.post(url, data=json.dumps(payload), content_type='application/json')

    def _pdf(self, response):
        self.assertEqual(response.status_code, 200, response.content[:500])
        self.assertEqual(response['Content-Type'], 'application/pdf')
        return PdfReader(BytesIO(response.content))

    def test_mirror_sheet_is_exactly_two_pages_for_many_items(self):
        for n in (5, 12, 20):
            for cols in (1, 2):
                reader = self._pdf(self._post({
                    'title': 'T', 'mirror': True, 'columns': cols,
                    'items': [{'example_id': e.id} for e in self.examples[:n]],
                }))
                self.assertEqual(len(reader.pages), 2, f'{n} items / {cols} col should be 2 pages')

    def test_two_column_answer_page_reverses_column_order_when_mirrored(self):
        # 6 items, 2 cols -> col A = items 1-3, col B = items 4-6.
        # On the mirrored answer page the columns are swapped so that, once the
        # sheet is flipped, each answer lands under its own column.
        html = self._post({
            'title': 'T', 'mirror': True, 'columns': 2,
            'items': [{'example_id': e.id} for e in self.examples[:6]],
        }, debug_html=True).content.decode()
        answers_page = html.split('<div class="page apage')[1]
        a4 = self.examples[3].answers.first().answer
        a1 = self.examples[0].answers.first().answer
        self.assertLess(answers_page.index(f'>{a4}<'), answers_page.index(f'>{a1}<'))

    def test_answer_page_carries_the_real_answers(self):
        reader = self._pdf(self._post({
            'title': 'T', 'mirror': True,
            'items': [{'example_id': e.id} for e in self.examples[:4]],
        }))
        answer_text = re.sub(r'\s+', '', reader.pages[1].extract_text() or '')
        for e in self.examples[:4]:
            self.assertIn(e.answers.first().answer, answer_text)

    def test_no_answer_page_when_disabled(self):
        reader = self._pdf(self._post({
            'title': 'T', 'show_answer_page': False,
            'items': [{'example_id': e.id} for e in self.examples[:6]],
        }))
        self.assertEqual(len(reader.pages), 1)

    def test_mirror_transform_present_only_in_mirror_mode(self):
        on = self._post({'title': 'T', 'mirror': True, 'debug': 1,
                         'items': [{'example_id': self.examples[0].id}]}, debug_html=True)
        off = self._post({'title': 'T', 'mirror': False,
                          'items': [{'example_id': self.examples[0].id}]}, debug_html=True)
        self.assertIn('scaleX(-1)', on.content.decode())
        # the rule exists in CSS but is scoped to .mirror; the answer page
        # itself must not carry the class when mirror is off
        self.assertNotIn('class="page mirror"', off.content.decode())

    def test_ad_hoc_items_without_ids(self):
        reader = self._pdf(self._post({
            'title': 'T', 'mirror': True,
            'items': [{'example': '2 + 2', 'answer': '4'}, {'example': '3 + 3', 'answer': '6'}],
        }))
        self.assertEqual(len(reader.pages), 2)

    def test_rejects_teacher_owned_examples(self):
        teacher = Teacher.objects.create(email='po@e.com', password='x',
                                         first_name='P', last_name='O')
        owned = Example.objects.create(example='9 + 9', input_type='INLINE',
                                       owner_teacher=teacher)
        Answer.objects.create(example=owned, answer='18')
        resp = self._post({'title': 'T', 'items': [{'example_id': owned.id}]})
        self.assertEqual(resp.status_code, 403)
