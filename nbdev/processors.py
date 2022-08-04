# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/09_processors.ipynb.

# %% auto 0
__all__ = ['DEFAULT_FM_KEYS', 'nbflags_', 'cell_lang', 'add_links', 'strip_ansi', 'strip_hidden_metadata', 'hide_', 'hide_line',
           'filter_stream_', 'clean_magics', 'lang_identify', 'rm_header_dash', 'rm_export', 'clean_show_doc',
           'exec_show_docs', 'populate_language', 'insert_warning', 'add_show_docs', 'is_frontmatter', 'yml2dict',
           'yaml_str', 'nb_fmdict', 'construct_fm', 'insert_frontmatter', 'infer_frontmatter']

# %% ../nbs/09_processors.ipynb 2
import ast

from .read import *
from .imports import *
from .process import *
from .showdoc import *
from .doclinks import *

from execnb.nbio import *
from execnb.shell import *
from fastcore.imports import *
from fastcore.xtras import *
from yaml import load, SafeLoader, dump
import sys

# %% ../nbs/09_processors.ipynb 9
def nbflags_(nbp, cell, *args):
    "Hide cell from output"
    nbp.nb._nbflags = args

# %% ../nbs/09_processors.ipynb 11
def cell_lang(cell): return nested_attr(cell, 'metadata.language', 'python')

def add_links(cell):
    "Add links to markdown cells"
    nl = NbdevLookup()
    if cell.cell_type == 'markdown': cell.source = nl.linkify(cell.source)
    for o in cell.get('outputs', []):
        if hasattr(o, 'data') and hasattr(o['data'], 'text/markdown'):
            o.data['text/markdown'] = [nl.link_line(s) for s in o.data['text/markdown']]

# %% ../nbs/09_processors.ipynb 14
_re_ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(cell):
    "Strip Ansi Characters."
    for outp in cell.get('outputs', []):
        if outp.get('name')=='stdout': outp['text'] = [_re_ansi_escape.sub('', o) for o in outp.text]

# %% ../nbs/09_processors.ipynb 16
def strip_hidden_metadata(cell):
    '''Strips "hidden" metadata property from code cells so it doesn't interfere with docs rendering'''
    if cell.cell_type == 'code' and 'metadata' in cell: cell.metadata.pop('hidden',None)

# %% ../nbs/09_processors.ipynb 17
def hide_(nbp, cell):
    "Hide cell from output"
    del(cell['source'])

# %% ../nbs/09_processors.ipynb 19
def _re_hideline(lang=None): return re.compile(fr'{langs[lang]}\|\s*hide_line\s*$', re.MULTILINE)

def hide_line(cell):
    "Hide lines of code in code cells with the directive `hide_line` at the end of a line of code"
    lang = cell_lang(cell)
    if cell.cell_type == 'code' and _re_hideline(lang).search(cell.source):
        cell.source = '\n'.join([c for c in cell.source.splitlines() if not _re_hideline(lang).search(c)])

# %% ../nbs/09_processors.ipynb 21
def filter_stream_(nbp, cell, *words):
    "Remove output lines containing any of `words` in `cell` stream output"
    if not words: return
    for outp in cell.get('outputs', []):
        if outp.output_type == 'stream':
            outp['text'] = [l for l in outp.text if not re.search('|'.join(words), l)]

# %% ../nbs/09_processors.ipynb 23
_magics_pattern = re.compile(r'^\s*(%%|%).*', re.MULTILINE)

def clean_magics(cell):
    "A preprocessor to remove cell magic commands"
    if cell.cell_type == 'code': cell.source = _magics_pattern.sub('', cell.source).strip()

# %% ../nbs/09_processors.ipynb 25
_langs = 'bash|html|javascript|js|latex|markdown|perl|ruby|sh|svg'
_lang_pattern = re.compile(rf'^\s*%%\s*({_langs})\s*$', flags=re.MULTILINE)

def lang_identify(cell):
    "A preprocessor to identify bash/js/etc cells and mark them appropriately"
    if cell.cell_type == 'code':
        lang = _lang_pattern.findall(cell.source)
        if lang: cell.metadata.language = lang[0]

# %% ../nbs/09_processors.ipynb 28
_re_hdr_dash = re.compile(r'^#+\s+.*\s+-\s*$', re.MULTILINE)

def rm_header_dash(cell):
    "Remove headings that end with a dash -"
    if cell.source:
        src = cell.source.strip()
        if cell.cell_type == 'markdown' and src.startswith('#') and src.endswith(' -'): del(cell['source'])

# %% ../nbs/09_processors.ipynb 30
_hide_dirs = {'export','exporti', 'hide','default_exp'}

# %% ../nbs/09_processors.ipynb 31
def rm_export(cell):
    "Remove cells that are exported or hidden"
    if cell.directives_:
        if cell.directives_.keys() & _hide_dirs: del(cell['source'])

# %% ../nbs/09_processors.ipynb 34
_re_showdoc = re.compile(r'^show_doc', re.MULTILINE)
def _is_showdoc(cell): return cell['cell_type'] == 'code' and _re_showdoc.search(cell.source)

def clean_show_doc(cell):
    "Remove ShowDoc input cells"
    if not _is_showdoc(cell): return
    cell.source = '#|output: asis\n#| echo: false\n' + cell.source

# %% ../nbs/09_processors.ipynb 35
_imps = {ast.Import, ast.ImportFrom}

def _show_docs(trees):
    return [t for t in trees if isinstance(t,ast.Expr) and nested_attr(t, 'value.func.id')=='show_doc']

_show_dirs = {'export','exports','exporti','exec_doc'}

def _do_eval(cell):
    if cell_lang(cell) != 'python': return
    trees = cell.parsed_()
    if cell.cell_type != 'code' or not trees: return
    if cell.directives_.get('eval:', [''])[0].lower() == 'false': return
    if cell.directives_.keys() & _show_dirs or filter_ex(trees, risinstance(_imps)): return True
    if _show_docs(trees): return True

# %% ../nbs/09_processors.ipynb 36
class exec_show_docs:
    "Execute cells needed for `show_docs` output, including exported cells and imports"
    def __init__(self, nb):
        self.k = CaptureShell()
        if nb_lang(nb) == 'python': self.k.run_cell('from nbdev.showdoc import show_doc')

    def __call__(self, cell):
        flags = getattr(cell.nb, '_nbflags', [])
        if 'skip_showdoc' in flags: return
        if _do_eval(cell): self.k.cell(cell)
        if self.k.exc: raise Exception(f'Error: cell {cell.idx_}:\n{cell.source}') from self.k.exc[1]

# %% ../nbs/09_processors.ipynb 39
def populate_language(nb):
    "Insert cell language indicator based on notebook metadata.  You should to use this before `lang_identify`"
    for cell in nb.cells:
        if cell.cell_type == 'code': cell.metadata.language = nb_lang(nb)

# %% ../nbs/09_processors.ipynb 42
def insert_warning(nb):
    "Insert Autogenerated Warning Into Notebook after the first cell."
    content = "<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->"
    nb.cells.insert(1, mk_cell(content, 'markdown'))

# %% ../nbs/09_processors.ipynb 46
_def_types = (ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)
def _def_names(cell, shown):
    return [showdoc_nm(o) for o in concat(cell.parsed_())
            if isinstance(o,_def_types) and o.name not in shown and o.name[0]!='_']

def _get_nm(tree):
    i = tree.value.args[0]
    if hasattr(i, 'id'): val = i.id
    else: val = try_attrs(i.value, 'id', 'func', 'attr')
    return f'{val}.{i.attr}' if isinstance(i, ast.Attribute) else i.id

# %% ../nbs/09_processors.ipynb 47
def add_show_docs(nb):
    "Add show_doc cells after exported cells, unless they are already documented"
    def _want(c):
        return c.source and c.cell_type=='code' and ('export' in c.directives_ or 'exports' in c.directives_)

    exports = L(cell for cell in nb.cells if _want(cell))
    trees = nb.cells.map(NbCell.parsed_).concat()
    shown_docs = {_get_nm(t) for t in _show_docs(trees)}
    for cell in reversed(exports):
        if cell_lang(cell) != 'python': 
            raise ValueError(f'{cell.metadata.language} cell attempted export:\n{cell.source}')
        for nm in _def_names(cell, shown_docs):
            nb.cells.insert(cell.idx_+1, mk_cell(f'show_doc({nm})'))

# %% ../nbs/09_processors.ipynb 51
_re_title = re.compile(r'^#\s+(.*)[\n\r]+(?:^>\s+(.*))?', flags=re.MULTILINE)
_re_fm = re.compile(r'^---(.*\S+.*)---', flags=re.DOTALL)
_re_defaultexp = re.compile(r'^\s*#\|\s*default_exp\s+(\S+)', flags=re.MULTILINE)

def _celltyp(nb, cell_type): return nb.cells.filter(lambda c: c.cell_type == cell_type)
def is_frontmatter(nb): return _celltyp(nb, 'raw').filter(lambda c: _re_fm.search(c.get('source', '')))
def _istitle(cell): 
    txt = cell.get('source', '')
    return bool(_re_title.search(txt)) if txt else False


# %% ../nbs/09_processors.ipynb 50
def yml2dict(s:str, rm_fence=True):
    "convert a string that is in a yaml format to a dict"
    if rm_fence: 
        match = _re_fm.search(s.strip())
        if match: s = match.group(1)
    return load(s, Loader=SafeLoader)

# %% ../nbs/09_processors.ipynb 52
def _default_exp(nb):
    "get the default_exp from a notebook"
    code_src = nb.cells.filter(lambda x: x.cell_type == 'code').attrgot('source')
    default_exp = first(code_src.filter().map(_re_defaultexp.search).filter())
    return default_exp.group(1) if default_exp else None

# %% ../nbs/09_processors.ipynb 56
def yaml_str(s:str):
    "Create a valid YAML string from `s`"
    if s[0]=='"' and s[-1]=='"': return s
    res = s.replace('\\', '\\\\').replace('"', r'\"')
    return f'"{res}"'

# %% ../nbs/09_processors.ipynb 57
def nb_fmdict(nb, remove=True): 
    "Infer the front matter from a notebook's markdown formatting"
    md_cells = _celltyp(nb, 'markdown').filter(_istitle)
    if not md_cells: return {}
    cell = md_cells[0]
    title,desc=_re_title.match(cell.source).groups()
    if title:
        flags = re.findall('^-\s+(.*)', cell.source, flags=re.MULTILINE)
        flags = [s.split(':', 1) for s in flags if ':' in s] if flags else []
        flags = merge({k:v for k,v in flags if k and v}, 
                      {'title':yaml_str(title)}, {'description':yaml_str(desc)} if desc else {})
        if remove: cell['source'] = None
        return yml2dict('\n'.join([f"{k}: {flags[k]}" for k in flags]))
    else: return {}

# %% ../nbs/09_processors.ipynb 60
def _replace_fm(d:dict, # dictionary you wish to conditionally change
                k:str,  # key to check 
                val:str,# value to check if d[k] == v
                repl_dict:dict #dictionary that will be used as a replacement 
               ):
    "replace key `k` in dict `d` if d[k] == val with `repl_dict`"
    if str(d.get(k, '')).lower().strip() == str(val.lower()).strip():
        d.pop(k)
        d = merge(d, repl_dict)
    return d

def _fp_alias(d):
    "create aliases for fastpages front matter to match Quarto front matter."
    d = _replace_fm(d, 'search_exclude', 'true', {'search':'false'})
    d = _replace_fm(d, 'hide', 'true', {'draft': 'true'})
    d = _replace_fm(d, 'comments', 'true', {'comments': {'hypothesis': {'theme': 'clean'}}})
    return d

# %% ../nbs/09_processors.ipynb 62
DEFAULT_FM_KEYS = ['title', 'description', 'author', 'image', 'categories', 'output-file', 'aliases', 'search', 'draft', 'comments']

def construct_fm(fmdict:dict, keys = DEFAULT_FM_KEYS):
    "construct front matter from a dictionary, but only for `keys`"
    if not fmdict: return None
    return '---\n'+dump(filter_keys(fmdict, in_(keys)))+'\n---'
    

# %% ../nbs/09_processors.ipynb 62
def insert_frontmatter(nb, fm_dict:dict, filter_dict_keys:list=DEFAULT_FM_KEYS):
    "Add frontmatter into notebook based on `filter_keys` that exist in `fmdict`."
    fm = construct_fm(fm_dict)
    if fm: nb.cells.insert(0, NbCell(0, dict(cell_type='raw', metadata={}, source=fm, directives_={})))

# %% ../nbs/09_processors.ipynb 65
def infer_frontmatter(nb):
    "Insert front matter if it doesn't exist automatically from nbdev styled markdown."
    raw_fm_cell = first(is_frontmatter(nb))
    raw_fm = yml2dict(raw_fm_cell.source) if raw_fm_cell else {}
    _exp = _default_exp(nb)
    _fmdict = merge(_fp_alias(nb_fmdict(nb)), {'output-file': _exp+'.html'} if _exp else {}, raw_fm)
    if 'title' in _fmdict: 
        if raw_fm: raw_fm_cell['source'] = None
        insert_frontmatter(nb, fm_dict=_fmdict)
