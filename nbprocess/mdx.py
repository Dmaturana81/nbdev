# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/06_mdx.ipynb (unless otherwise specified).

__all__ = ['default_pp_cfg', 'InjectMeta', 'StripAnsi', 'InsertWarning', 'RmEmptyCode', 'UpdateTags', 'HideInputLines',
           'FilterOutput', 'CleanFlags', 'CleanMagics', 'BashIdentify', 'CleanShowDoc', 'HTMLEscape', 'RmHeaderDash',
           'default_pps', 'mdx_exporter', 'nb2md']

# Cell
import re, uuid

from .read import get_config
from .processor import *
from nbconvert.preprocessors import ExtractOutputPreprocessor

from fastcore.basics import *
from fastcore.foundation import *
from traitlets.config import Config
from pathlib import Path
from html.parser import HTMLParser

# Cell
def default_pp_cfg():
    "Default Preprocessor Config for MDX export"
    c = Config()
    c.TagRemovePreprocessor.remove_cell_tags = ("remove_cell", "hide")
    c.TagRemovePreprocessor.remove_all_outputs_tags = ("remove_output", "remove_outputs", "hide_output", "hide_outputs")
    c.TagRemovePreprocessor.remove_input_tags = ('remove_input', 'remove_inputs', "hide_input", "hide_inputs")
    return c

# Cell
def _mdx_exporter(pps, cfg=None, tpl_file='ob.tpl'):
    "An mdx notebook exporter which composes preprocessors"
    cfg = cfg or default_pp_cfg()
    cfg.MarkdownExporter.preprocessors = pps or []
    tmp_dir = Path(__file__).parent/'templates/'
    tpl_file = tmp_dir/f"{tpl_file}"
    if not tpl_file.exists(): raise ValueError(f"{tpl_file} does not exist in {tmp_dir}")
    cfg.MarkdownExporter.template_file = str(tpl_file)
    return MarkdownExporter(config=cfg)

# Cell
def _run_preprocessor(pps, fname, display=False):
    "An mdx notebook exporter which composes preprocessors"
    exp = _mdx_exporter(pps)
    result = exp.from_filename(fname)
    if display: print(result[0])
    return result

# Cell
_re_meta= r'^\s*#(?:cell_meta|meta):\S+\s*[\n\r]'

@preprocess_cell
def InjectMeta(cell):
    "Inject metadata into a cell for further preprocessing with a comment."
    _pattern = r'(^\s*#(?:cell_meta|meta):)(\S+)(\s*[\n\r])'
    if cell.cell_type == 'code' and re.search(_re_meta, cell.source, flags=re.MULTILINE):
        cell_meta = re.findall(_pattern, cell.source, re.MULTILINE)
        d = cell.metadata.get('nbprocess', {})
        for _, m, _ in cell_meta:
            if '=' in m:
                k,v = m.split('=')
                d[k] = v
            else: print(f"Warning cell_meta:{m} does not have '=' will be ignored.")
        cell.metadata['nbprocess'] = d

# Cell
_re_ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

@preprocess_cell
def StripAnsi(cell):
    "Strip Ansi Characters."
    for o in cell.get('outputs', []):
        if o.get('name') == 'stdout': o['text'] = _re_ansi_escape.sub('', o.text)

# Cell
@preprocess
def InsertWarning(nb):
    """Insert Autogenerated Warning Into Notebook after the first cell."""
    content = "<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->"
    mdcell = AttrDict(cell_type='markdown', id=uuid.uuid4().hex[:36], metadata={}, source=content)
    nb.cells.insert(1, mdcell)

# Cell
def _keepCell(cell): return cell['cell_type'] != 'code' or cell.source.strip()

@preprocess
def RmEmptyCode(nb):
    "Remove empty code cells."
    nb.cells = filter(_keepCell,nb.cells)

# Cell
@preprocess_cell
def UpdateTags(cell):
    root = cell.metadata.get('nbprocess', {})
    tags = root.get('tags', root.get('tag')) # allow the singular also
    if tags: cell.metadata['tags'] = cell.metadata.get('tags', []) + tags.split(',')

# Cell
@preprocess_cell
def HideInputLines(cell):
    "Hide lines of code in code cells with the comment `#meta_hide_line` at the end of a line of code."
    tok = '#meta_hide_line'
    if cell.cell_type == 'code' and tok in cell.source:
        cell.source = '\n'.join([c for c in cell.source.splitlines() if not c.strip().endswith(tok)])

# Cell
@preprocess_cell
def FilterOutput(cell):
    root = cell.metadata.get('nbprocess', {})
    words = root.get('filter_words', root.get('filter_word'))
    # import ipdb; ipdb.set_trace()
    if 'outputs' in cell and words:
        _re = f"^(?!.*({'|'.join(words.split(','))}))"
        for o in cell.outputs:
            if o.name == 'stdout':
                filtered_lines = [l for l in o['text'].splitlines() if re.findall(_re, l)]
                o['text'] = '\n'.join(filtered_lines)

# Cell
_tst_flags = get_config()['tst_flags'].split('|')

@preprocess_cell
def CleanFlags(cell):
    "A preprocessor to remove Flags"
    if cell.cell_type != 'code': return
    for p in [re.compile(r'^#\s*{0}\s*'.format(f), re.MULTILINE) for f in _tst_flags]:
        cell.source = p.sub('', cell.source).strip()

# Cell
@preprocess_cell
def CleanMagics(cell):
    "A preprocessor to remove cell magic commands and #cell_meta: comments"
    pattern = re.compile(r'(^\s*(%%|%).+?[\n\r])|({0})'.format(_re_meta), re.MULTILINE)
    if cell.cell_type == 'code': cell.source = pattern.sub('', cell.source).strip()

# Cell
@preprocess_cell
def BashIdentify(cell):
    "A preprocessor to identify bash commands and mark them appropriately"
    pattern = re.compile('^\s*!', flags=re.MULTILINE)
    if cell.cell_type == 'code' and pattern.search(cell.source):
        cell.metadata.magics_language = 'bash'
        cell.source = pattern.sub('', cell.source).strip()

# Cell
_re_showdoc = re.compile(r'^ShowDoc', re.MULTILINE)

def _isShowDoc(cell):
    "Return True if cell contains ShowDoc."
    return cell['cell_type'] == 'code' and _re_showdoc.search(cell.source)

@preprocess_cell
def CleanShowDoc(cell):
    "Ensure that ShowDoc output gets cleaned in the associated notebook."
    _re_html = re.compile(r'<HTMLRemove>.*</HTMLRemove>', re.DOTALL)
    if not _isShowDoc(cell): return
    all_outs = [o['data'] for o in cell.outputs if 'data' in o]
    html_outs = [o['text/html'] for o in all_outs if 'text/html' in o]
    if len(html_outs) != 1: return
    cleaned_html = self._re_html.sub('', html_outs[0])
    return AttrDict({'cell_type':'raw', 'id':cell.id, 'metadata':cell.metadata, 'source':cleaned_html})

# Cell
class _HTMLdf(HTMLParser):
    "HTML Parser that finds a dataframe."
    df,scoped = False,False
    def handle_starttag(self, tag, attrs):
        if tag == 'style' and 'scoped' in dict(attrs): self.scoped=True
    def handle_data(self, data):
        if '.dataframe' in data and self.scoped: self.df=True
    def handle_endtag(self, tag):
        if tag == 'style': self.scoped=False

    @classmethod
    def search(cls, x):
        parser = cls()
        parser.feed(x)
        return parser.df

# Cell
@preprocess_cell
def HTMLEscape(cell):
    "Place HTML in a codeblock and surround it with a <HTMLOutputBlock> component."
    if cell.cell_type !='code': return
    for o in cell.outputs:
        if nested_idx(o, 'data', 'text/html'):
            cell.metadata.html_output = True
            html = o['data']['text/html']
            cell.metadata.html_center = not _HTMLdf.search(html)
            o['data']['text/html'] = '```html\n'+html.strip()+'\n```'

# Cell
_re_hdr_dash = re.compile(r'^#+\s+.*\s+-\s*$', re.MULTILINE)

@preprocess_cell
def RmHeaderDash(cell):
    "Remove headings that end with a dash -"
    if cell.cell_type == 'markdown':
        exclude = {l.strip() for l in _re_hdr_dash.findall(cell.source)}
        if exclude:
            lines = [l for l in cell.source.splitlines() if l not in exclude]
            cell.source = '\n'.join(lines)

# Cell
def default_pps(c):
    "Default Preprocessors for MDX export"
    return [InjectMeta, CleanMagics, BashIdentify, UpdateTags, InsertWarning, TagRemovePreprocessor,
            CleanFlags, CleanShowDoc, RmEmptyCode, StripAnsi, HideInputLines, RmHeaderDash,
            ExtractAttachmentsPreprocessor, ExtractOutputPreprocessor, HTMLEscape]

# Cell
def mdx_exporter(tpl_file, cfg=None, pps=None):
    "An mdx notebook exporter which composes preprocessors"
    pps = pps or default_pps(cfg)
    return _mdx_exporter(pps, cfg, tpl_file=tpl_file)

# Cell
def nb2md(fname, exp=None, dest=None, cfg=None, pps=None, tpl_file='ob.tpl'):
    "Convert notebook to markdown and export attached/output files"
    if isinstance(dest,Path): dest=dest.name
    file = Path(fname)
    assert file.name.endswith('.ipynb'), f'{fname} is not a notebook.'
    assert file.is_file(), f'file {fname} not found.'
    print(f"converting: {file}")
    exp = mdx_exporter(cfg=cfg, pps=pps, tpl_file=tpl_file)
    # https://gitlab.kwant-project.org/solidstate/lectures/-/blob/master/execute.py
    fw = FilesWriter()

    try:
        md = exp.from_filename(fname, resources=dict(unique_key=file.stem, output_files_dir=file.stem))
        if dest: fw.build_directory = dest
        return fw.write(*md, notebook_name=file.stem)
    except Exception as e: print(e)