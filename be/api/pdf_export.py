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
import io
import random
import re
from collections import deque

from pypdf import PdfReader, PdfWriter, Transformation

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
# Row / chunk layout engine
#
# Items are packed into display "rows" (up to `columns` compact items side
# by side, or one wide item with its answer-line block per row), each with
# an estimated height in mm — used both for per-row min-height/answer-blank
# sizing (both per_page modes) and, for per_page == 1, to split a sheet's
# rows into height-bounded page chunks (_chunk_rows below). per_page == 2
# no longer chunks by estimated height at all — see the imposition section
# further down, which lets WeasyPrint's real pagination decide instead.
# ---------------------------------------------------------------------------

_FULL_BUDGET_MM = 250
_FULL_HEAD_RESERVE_MM = 30       # header + meta (+ note) reserved on chunk 0 of a full page
_FULL_CONT_HEAD_RESERVE_MM = 14  # lighter header reserved on a continuation full page

# ---------------------------------------------------------------------------
# 2-per-A4 imposition (per_page == 2)
#
# Each group's worksheet is rendered as its own standalone half-A4 document
# (pdf/sheet_half.html) and left to WeasyPrint's real CSS pagination — no
# Python height guessing, so a half can never overflow its own page. Pairs of
# sheets' resulting pages are then imposed (top/bottom) onto shared A4 pages
# with pypdf, mirroring real print-shop "2-up" imposition instead of trying
# to precompute whether content fits.
# ---------------------------------------------------------------------------

_MM_TO_PT = 72 / 25.4
_A4_WIDTH_MM = 210
_A4_HEIGHT_MM = 297
_HALF_HEIGHT_MM = 148.5
_A4_WIDTH_PT = _A4_WIDTH_MM * _MM_TO_PT
_A4_HEIGHT_PT = _A4_HEIGHT_MM * _MM_TO_PT
_HALF_HEIGHT_PT = _HALF_HEIGHT_MM * _MM_TO_PT

# Cut line + scissors mark, drawn once as a standalone full-A4 overlay and
# merged onto every imposed page — same SVG mark as the old .half+.half CSS,
# just positioned at the fixed physical midline instead of a DOM sibling.
_CUTLINE_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  @page { size: 210mm 297mm; margin: 0; }
  body { margin: 0; }
  .cutline {
    position: absolute;
    top: 148.5mm;
    left: 12mm;
    width: 186mm;
    border-top: 0.4mm dashed #999;
  }
  .scissors {
    position: absolute;
    top: 148.5mm;
    left: 50%;
    width: 7mm;
    height: 7mm;
    transform: translate(-50%, -50%);
    background-color: #fff;
    background-repeat: no-repeat;
    background-position: center;
    background-size: 5mm 5mm;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23888' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='6' cy='6' r='3'/%3E%3Ccircle cx='6' cy='18' r='3'/%3E%3Cline x1='20' y1='4' x2='8.12' y2='15.88'/%3E%3Cline x1='14.47' y1='14.48' x2='20' y2='20'/%3E%3Cline x1='8.12' y1='8.12' x2='12' y2='12'/%3E%3C/svg%3E");
  }
</style></head><body>
<div class="cutline"></div>
<div class="scissors"></div>
</body></html>"""


def _render_pdf(html_string, HTML):
    return HTML(string=html_string).write_pdf()


def _render_sheet_reader(sheet, base_context, HTML):
    ctx = {**base_context, 'group': sheet['group'], 'rows': sheet['rows']}
    html_string = render_to_string('pdf/sheet_half.html', ctx)
    return PdfReader(io.BytesIO(_render_pdf(html_string, HTML)))


def _cutline_overlay_reader(HTML):
    return PdfReader(io.BytesIO(_render_pdf(_CUTLINE_HTML, HTML)))


def _impose_pair(writer, top_reader, bottom_reader, cutline_page):
    top_pages = top_reader.pages if top_reader else []
    bottom_pages = bottom_reader.pages if bottom_reader else []
    for i in range(max(len(top_pages), len(bottom_pages))):
        page = writer.add_blank_page(width=_A4_WIDTH_PT, height=_A4_HEIGHT_PT)
        if i < len(top_pages):
            page.merge_transformed_page(top_pages[i], Transformation().translate(ty=_HALF_HEIGHT_PT))
        if i < len(bottom_pages):
            page.merge_page(bottom_pages[i])
        page.merge_page(cutline_page)


def _render_two_up_pdf(base_context, sheets, cover_page, key_sheets, HTML):
    """Build the full per_page==2 output: optional cover, each pair of sheets
    imposed 2-up onto shared A4 pages, optional answer key — concatenated
    with pypdf into one PdfWriter and returned as bytes."""
    writer = PdfWriter()

    if cover_page:
        cover_ctx = {
            **base_context, 'per_page': 1, 'pages_full': [], 'pages_half': [],
            'key_sheets': [], 'cover_page': True,
        }
        cover_html = render_to_string('pdf/test_sheet.html', cover_ctx)
        for page in PdfReader(io.BytesIO(_render_pdf(cover_html, HTML))).pages:
            writer.add_page(page)

    cutline_page = _cutline_overlay_reader(HTML).pages[0]
    for i in range(0, len(sheets), 2):
        pair = sheets[i:i + 2]
        if len(pair) == 1:
            pair = [pair[0], pair[0]]
        top_sheet, bottom_sheet = pair
        top_reader = _render_sheet_reader(top_sheet, base_context, HTML)
        bottom_reader = _render_sheet_reader(bottom_sheet, base_context, HTML)
        _impose_pair(writer, top_reader, bottom_reader, cutline_page)

    if key_sheets:
        key_ctx = {
            **base_context, 'per_page': 1, 'pages_full': [], 'pages_half': [],
            'key_sheets': key_sheets, 'cover_page': False,
        }
        key_html = render_to_string('pdf/test_sheet.html', key_ctx)
        for page in PdfReader(io.BytesIO(_render_pdf(key_html, HTML))).pages:
            writer.add_page(page)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _resolve_wide(input_type, plain_len, answer_lines):
    """An item is 'wide' (its own full-width row with an answer-line block)
    if its type needs room, the teacher forced it via an explicit override,
    or the text is too long to sit comfortably in a compact column."""
    if answer_lines is not None:
        return answer_lines > 0
    if input_type in ('WORD', 'VAR'):
        return True
    return plain_len > 45


def _row_metrics(compact, spacing_factor):
    base = 9 if compact else 13
    return {
        'row_h': round(base * spacing_factor, 1),
        'header_h': round((5 if compact else 6) * spacing_factor, 1),
        'line_h': round((5 if compact else 6) * spacing_factor, 1),
        'gap': round(2 * spacing_factor, 2),
    }


def _build_rows(built_items, columns, metrics, default_answer_lines):
    rows = []
    bucket = []

    def flush_bucket():
        if bucket:
            rows.append({
                'wide': False,
                'items': list(bucket),
                'height_mm': round(metrics['row_h'] + metrics['gap'], 1),
            })
            bucket.clear()

    for item in built_items:
        if item['wide']:
            flush_bucket()
            lines = item['answer_lines'] if item['answer_lines'] is not None else default_answer_lines
            rows.append({
                'wide': True,
                'items': [item],
                'height_mm': round(metrics['header_h'] + lines * metrics['line_h'] + metrics['gap'], 1),
                'blank_h_mm': round(lines * metrics['line_h'], 1),
            })
        else:
            bucket.append(item)
            if len(bucket) >= columns:
                flush_bucket()
    flush_bucket()
    return rows


def _row_structure(built_items, columns):
    """The wide/compact bucket pattern of an ordered item list: a sequence of
    {'wide': True} or {'wide': False, 'count': n} slots. Group A (the
    teacher's own order) defines this once; B–D's shuffled variants are then
    forced through the same pattern (see `_apply_structure`) so a reshuffle
    can't land a wide item mid-bucket and silently make one group's sheet
    taller than another's — which is what let one half of a shared A4
    overflow onto an extra page while the other half didn't."""
    structure = []
    bucket = 0
    for item in built_items:
        if item['wide']:
            if bucket:
                structure.append({'wide': False, 'count': bucket})
                bucket = 0
            structure.append({'wide': True})
        else:
            bucket += 1
            if bucket >= columns:
                structure.append({'wide': False, 'count': bucket})
                bucket = 0
    if bucket:
        structure.append({'wide': False, 'count': bucket})
    return structure


def _apply_structure(built_items, structure):
    """Reorder built_items (in whatever order they were shuffled into) to
    match `structure`'s wide/compact slot sequence — wide items fill wide
    slots and compact items fill compact slots, each pool keeping its
    shuffled relative order. Same items, same total row count and heights
    as the sheet `structure` was derived from."""
    wide_pool = deque(it for it in built_items if it['wide'])
    compact_pool = deque(it for it in built_items if not it['wide'])
    ordered = []
    for slot in structure:
        if slot['wide']:
            ordered.append(wide_pool.popleft())
        else:
            for _ in range(slot['count']):
                ordered.append(compact_pool.popleft())
    return ordered


def _chunk_rows(rows, budget_mm, head_reserve_mm, cont_reserve_mm):
    """Split a sheet's rows into height-bounded batches, one per physical
    page (per_page == 1 only — per_page == 2 lets WeasyPrint paginate for
    real instead, see _render_two_up_pdf)."""
    if not rows:
        return [[]]
    chunks = []
    current = []
    used = head_reserve_mm
    for row in rows:
        if current and used + row['height_mm'] > budget_mm:
            chunks.append(current)
            current = []
            used = cont_reserve_mm
        current.append(row)
        used += row['height_mm']
    chunks.append(current)
    return chunks


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

    # Each item is either {example_id, points} (library example) or
    # {example, answer, points} (ad-hoc, e.g. freshly generated, not stored).
    entries = []
    try:
        for it in items:
            points = float(1 if it.get('points') in (None, '') else it['points'])
            input_type = it.get('input_type')
            input_type = str(input_type).upper() if input_type else None
            answer_lines = it.get('answer_lines')
            answer_lines = None if answer_lines in (None, '') else max(0, min(6, int(answer_lines)))
            if it.get('example_id') is not None:
                entries.append({
                    'id': int(it['example_id']), 'points': points,
                    'input_type': input_type, 'answer_lines': answer_lines,
                })
            else:
                entries.append({
                    'id': None,
                    'example': str(it['example']),
                    'answer': str(it.get('answer') or ''),
                    'points': points,
                    'input_type': input_type,
                    'answer_lines': answer_lines,
                })
    except (KeyError, TypeError, ValueError):
        return Response(
            {'error': 'items must be [{example_id, points}] or [{example, answer, points}]'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ordered_ids = [e['id'] for e in entries if e['id'] is not None]
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
    cover_page = bool(data.get('cover_page', False))
    show_header = bool(data.get('show_header', True))
    header_text = (data.get('header_text') or '').strip()

    try:
        groups = max(1, min(4, int(data.get('groups', 1))))
    except (TypeError, ValueError):
        groups = 1
    per_page = 2 if str(data.get('per_page', 1)) == '2' else 1

    try:
        columns = max(1, min(4, int(data.get('columns', 2))))
    except (TypeError, ValueError):
        columns = 2
    try:
        default_answer_lines = max(1, min(6, int(data.get('default_answer_lines', 4))))
    except (TypeError, ValueError):
        default_answer_lines = 4

    # Vertical spacing between examples: 8–64 "px", 24 = the original layout.
    try:
        spacing = max(8, min(64, int(data.get('spacing', 24))))
    except (TypeError, ValueError):
        spacing = 24
    spacing_factor = spacing / 24.0

    def build_item(entry, number):
        if entry['id'] is not None:
            ex = by_id[entry['id']]
            answer = ex.answers.first()
            text = ex.example or ''
            answer_text = answer.answer if answer else ''
            input_type = entry.get('input_type') or ex.input_type or 'INLINE'
        else:
            text = entry['example']
            answer_text = entry['answer']
            input_type = entry.get('input_type') or 'INLINE'
        # the sheet draws its own "= ______" answer blank / answer lines
        text = re.sub(r'=\s*\?\s*$', '', text).rstrip()
        plain_len = _plain_len(text)
        answer_lines = entry.get('answer_lines')
        return {
            'number': number,
            'points': _fmt_points(entry['points']),
            'html': latex_to_html(text),
            'answer_html': latex_to_html(answer_text),
            'input_type': input_type,
            'answer_lines': answer_lines,
            'wide': _resolve_wide(input_type, plain_len, answer_lines),
        }

    total_points = _fmt_points(sum(e['points'] for e in entries))
    compact = per_page == 2
    metrics = _row_metrics(compact, spacing_factor)

    # Group A keeps the teacher's order and defines the row/height structure
    # (which slots are wide vs. compact-run); B–D are deterministic reshuffles
    # forced through that same structure so every group's sheet has identical
    # total height — otherwise a shuffle could land a wide item mid-bucket in
    # one group but not another, making that group's sheet taller and
    # overflowing onto an extra (mostly blank) shared page.
    shuffle_seed = [e['id'] if e['id'] is not None else e.get('example', '') for e in entries]
    sheets = []
    base_structure = None
    for gi in range(groups):
        if gi == 0:
            built_items = [build_item(e, n) for n, e in enumerate(entries, start=1)]
            base_structure = _row_structure(built_items, columns)
        else:
            shuffled = list(entries)
            random.Random(f'{sorted(map(str, shuffle_seed))}-{gi}').shuffle(shuffled)
            raw_items = [build_item(e, 0) for e in shuffled]
            built_items = _apply_structure(raw_items, base_structure)
            for n, it in enumerate(built_items, start=1):
                it['number'] = n
        sheets.append({
            'group': _GROUP_LETTERS[gi] if groups > 1 else '',
            'items': built_items,
            'rows': _build_rows(built_items, columns, metrics, default_answer_lines),
        })

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

    base_context = {
        'title': title,
        'class_name': class_name,
        'note': note,
        'show_points': show_points,
        'total_points': total_points,
        'has_groups': groups > 1,
        'show_header': show_header,
        'header_text': header_text,
        'columns': columns,
        'col_width_pct': round(100.0 / columns, 2),
        'row_gap_mm': metrics['gap'],
    }

    # Dev-only escape hatch: returns rendered HTML instead of a PDF, so the
    # template/row-building logic can be sanity-checked (curl/browser)
    # without a working WeasyPrint install. No longer used by the frontend —
    # the live preview now renders the real PDF via teacherPrintTest (see
    # apiClient.js) so it matches the download byte-for-byte.
    if per_page == 2:
        if request.GET.get('debug') == 'html':
            debug_ctx = {**base_context, 'group': sheets[0]['group'], 'rows': sheets[0]['rows']}
            return HttpResponse(
                render_to_string('pdf/sheet_half.html', debug_ctx),
                content_type='text/html; charset=utf-8',
            )
    else:
        # per_page == 1: each sheet's rows are still explicitly chunked into
        # page-budgeted batches (unchanged) — a single combined document
        # renders every sheet plus cover/key in one WeasyPrint call.
        pages_full = []
        for sheet in sheets:
            chunks = _chunk_rows(sheet['rows'], _FULL_BUDGET_MM, _FULL_HEAD_RESERVE_MM, _FULL_CONT_HEAD_RESERVE_MM)
            for ci, rows in enumerate(chunks):
                pages_full.append({
                    'group': sheet['group'],
                    'rows': rows,
                    'is_continuation': ci > 0,
                    'chunk_number': ci + 1,
                    'chunk_count': len(chunks),
                })
        context = {
            **base_context,
            'per_page': per_page,
            'pages_full': pages_full,
            'pages_half': [],
            'key_sheets': key_sheets,
            'cover_page': cover_page,
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

    if per_page == 2:
        # Each sheet is rendered as its own standalone half-A4 document and
        # imposed 2-up onto shared A4 pages — see _render_two_up_pdf. Real
        # WeasyPrint pagination per half means overflow past the cut line is
        # structurally impossible, not just unlikely.
        pdf_bytes = _render_two_up_pdf(base_context, sheets, cover_page, key_sheets, HTML)
    else:
        pdf_bytes = HTML(string=html).write_pdf()

    safe_title = re.sub(r'[^\w\- ]', '', title).strip().replace(' ', '_') or 'test'
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{safe_title}.pdf"'
    return response
