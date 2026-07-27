"""
================================================================================
 Module: pdf_export.py
 Description:
        PDF export of tests / worksheets for teachers (Fáza 2 — PDF tvorba).
        Builds an HTML sheet from selected examples and renders it to PDF
        with WeasyPrint. Example texts are stored as a small LaTeX subset
        (\\frac, \\sqrt, \\text, \\times, ...), converted here to plain
        HTML/CSS that WeasyPrint can lay out without JavaScript.
================================================================================
"""

import html as html_lib
import random
import re

from django.http import HttpResponse
from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Example, Teacher


# ---------------------------------------------------------------------------
# LaTeX subset → HTML
# ---------------------------------------------------------------------------

_SYMBOLS = {
    'times': '×',
    'cdot': '·',
    'div': '÷',
    'pm': '±',
    'le': '≤',
    'leq': '≤',
    'ge': '≥',
    'geq': '≥',
    'ne': '≠',
    'neq': '≠',
    'in': '∈',
    'notin': '∉',
    'infty': '∞',
    'rightarrow': '→',
    'percent': '%',
}

_MATHBB = {'R': 'ℝ', 'N': 'ℕ', 'Z': 'ℤ', 'Q': 'ℚ', 'C': 'ℂ'}

_SPACING = {';', ',', ':', '!', 'quad', 'qquad'}


def _read_group(s, i):
    """s[i] == '{'; return (raw_content, index_after_closing_brace)."""
    depth = 0
    start = i + 1
    while i < len(s):
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                return s[start:i], i + 1
        i += 1
    return s[start:], len(s)


def _read_token(s, i):
    """Read one token after ^ or _ : either a {...} group or a single char."""
    if i < len(s) and s[i] == '{':
        return _read_group(s, i)
    if i < len(s):
        return s[i], i + 1
    return '', i


def latex_to_html(text):
    """Convert the small LaTeX subset used by examples into inline HTML."""
    if text is None:
        return ''
    s = str(text)
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '\\':
            i += 1
            if i >= len(s):
                break
            # single-char commands: \; \, \: \! and literal \\ \{ \}
            if s[i] == '\\':
                out.append('<br>')
                i += 1
                continue
            if s[i] in '{}%':
                out.append(html_lib.escape(s[i]))
                i += 1
                continue
            if s[i] in ';,:!':
                out.append(' ')
                i += 1
                continue
            m = re.match(r'[a-zA-Z]+\*?', s[i:])
            if not m:
                i += 1
                continue
            cmd = m.group(0)
            i += len(cmd)
            if cmd in ('text', 'mathrm', 'textrm', 'mbox'):
                if i < len(s) and s[i] == '{':
                    content, i = _read_group(s, i)
                    out.append('<span class="txt">' + html_lib.escape(content) + '</span>')
                continue
            if cmd == 'frac':
                num, i = _read_group(s, i) if i < len(s) and s[i] == '{' else ('', i)
                den, i = _read_group(s, i) if i < len(s) and s[i] == '{' else ('', i)
                out.append(
                    '<span class="frac"><span class="num">' + latex_to_html(num) +
                    '</span><span class="den">' + latex_to_html(den) + '</span></span>'
                )
                continue
            if cmd == 'sqrt':
                idx = ''
                if i < len(s) and s[i] == '[':
                    end = s.find(']', i)
                    if end != -1:
                        idx = s[i + 1:end]
                        i = end + 1
                arg, i = _read_group(s, i) if i < len(s) and s[i] == '{' else _read_token(s, i)
                root = '<sup class="rootidx">' + latex_to_html(idx) + '</sup>' if idx else ''
                out.append(root + '√<span class="sqrtarg">' + latex_to_html(arg) + '</span>')
                continue
            if cmd == 'mathbb':
                arg, i = _read_group(s, i) if i < len(s) and s[i] == '{' else _read_token(s, i)
                out.append(_MATHBB.get(arg.strip(), arg))
                continue
            if cmd in ('begin', 'end'):
                if i < len(s) and s[i] == '{':
                    _, i = _read_group(s, i)
                if cmd == 'end':
                    pass
                continue
            if cmd in _SPACING:
                out.append(' ')
                continue
            if cmd in _SYMBOLS:
                out.append(_SYMBOLS[cmd])
                continue
            # unknown command — drop it, keep going
            continue
        if ch == '^':
            tok, i = _read_token(s, i + 1)
            out.append('<sup>' + latex_to_html(tok) + '</sup>')
            continue
        if ch == '_':
            tok, i = _read_token(s, i + 1)
            out.append('<sub>' + latex_to_html(tok) + '</sub>')
            continue
        if ch == '{':
            content, i = _read_group(s, i)
            out.append(latex_to_html(content))
            continue
        if ch in ('}', '&'):
            i += 1
            continue
        if ch == '$':
            i += 1
            continue
        out.append(html_lib.escape(ch))
        i += 1
    return ''.join(out).strip()


def _plain_len(latex_text):
    """Rough visible-character length of a LaTeX string (for layout heuristics)."""
    stripped = re.sub(r'\\[a-zA-Z]+\*?', '', str(latex_text or ''))
    return len(re.sub(r'[{}^_$\\]', '', stripped))


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------

_GROUP_LETTERS = ['A', 'B', 'C', 'D']


def _fmt_points(value):
    if value == int(value):
        return str(int(value))
    return ('%g' % value).replace('.', ',')


@api_view(['POST'])
def teacher_print_test(request):
    """Render selected examples into a printable PDF test / worksheet."""
    data = request.data

    teacher_id = data.get('teacher_id')
    if not teacher_id:
        return Response({'error': 'teacher_id required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        teacher = Teacher.objects.get(id=int(teacher_id))
    except (Teacher.DoesNotExist, TypeError, ValueError):
        return Response({'error': 'Teacher not found'}, status=status.HTTP_404_NOT_FOUND)

    items = data.get('items') or []
    if not isinstance(items, list) or not items:
        return Response({'error': 'items required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        ordered_ids = [int(it['example_id']) for it in items]
        points_by_id = {
            int(it['example_id']): float(1 if it.get('points') in (None, '') else it['points'])
            for it in items
        }
    except (KeyError, TypeError, ValueError):
        return Response({'error': 'items must be [{example_id, points}]'}, status=status.HTTP_400_BAD_REQUEST)

    examples = Example.objects.filter(id__in=ordered_ids).prefetch_related('answers')
    by_id = {ex.id: ex for ex in examples}
    missing = [eid for eid in ordered_ids if eid not in by_id]
    if missing:
        return Response({'error': f'Examples not found: {missing}'}, status=status.HTTP_404_NOT_FOUND)

    # Teachers may print their own examples and public (admin) content,
    # but never another teacher's private material.
    for ex in by_id.values():
        if ex.owner_teacher_id is not None and ex.owner_teacher_id != teacher.id:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    title = (data.get('title') or '').strip() or 'Písomná práca'
    class_name = (data.get('class_name') or '').strip()
    note = (data.get('note') or '').strip()
    show_points = bool(data.get('show_points', True))
    answer_key = bool(data.get('answer_key', False))

    try:
        groups = max(1, min(4, int(data.get('groups', 1))))
    except (TypeError, ValueError):
        groups = 1
    per_page = 2 if str(data.get('per_page', 1)) == '2' else 1

    def build_item(eid, number):
        ex = by_id[eid]
        answer = ex.answers.first()
        text = ex.example or ''
        # the sheet draws its own "= ______" answer blank
        text = re.sub(r'=\s*\?\s*$', '', text).rstrip()
        return {
            'number': number,
            'points': _fmt_points(points_by_id[eid]),
            'html': latex_to_html(text),
            'answer_html': latex_to_html(answer.answer if answer else ''),
            'wide': _plain_len(text) > 45,
        }

    total_points = _fmt_points(sum(points_by_id[eid] for eid in ordered_ids))

    # Group A keeps the teacher's order; B–D are deterministic reshuffles.
    sheets = []
    for gi in range(groups):
        ids = list(ordered_ids)
        if gi > 0:
            random.Random(f'{sorted(ordered_ids)}-{gi}').shuffle(ids)
        sheets.append({
            'group': _GROUP_LETTERS[gi] if groups > 1 else '',
            'items': [build_item(eid, n) for n, eid in enumerate(ids, start=1)],
        })

    if per_page == 2:
        pages = []
        for i in range(0, len(sheets), 2):
            pair = sheets[i:i + 2]
            if len(pair) == 1:
                pair = [pair[0], pair[0]]
            pages.append(pair)
    else:
        pages = [[sheet] for sheet in sheets]

    key_sheets = []
    if answer_key:
        for sheet in sheets:
            key_sheets.append({
                'group': sheet['group'],
                'answers': [
                    {'number': it['number'], 'answer_html': it['answer_html'] or '—'}
                    for it in sheet['items']
                ],
            })

    context = {
        'title': title,
        'class_name': class_name,
        'note': note,
        'show_points': show_points,
        'total_points': total_points,
        'per_page': per_page,
        'pages': pages,
        'key_sheets': key_sheets,
        'has_groups': groups > 1,
    }
    html = render_to_string('pdf/test_sheet.html', context)

    if request.GET.get('debug') == 'html':
        return HttpResponse(html, content_type='text/html; charset=utf-8')

    try:
        from weasyprint import HTML
    except Exception as exc:
        return Response(
            {'error': f'PDF engine unavailable: {exc}'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    pdf_bytes = HTML(string=html).write_pdf()

    safe_title = re.sub(r'[^\w\- ]', '', title).strip().replace(' ', '_') or 'test'
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{safe_title}.pdf"'
    return response
