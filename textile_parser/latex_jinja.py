from jinja2 import Environment, StrictUndefined, FileSystemLoader
from os.path import dirname, realpath, join

dir = realpath(dirname(__file__))
template_dir = join(dir, "../jinja_template")

def _get_env(**kwargs):
    return Environment(
    block_start_string=r'\BLOCK{',
    block_end_string='}',
    variable_start_string=r'\VAR{',
    variable_end_string='}',
    comment_start_string=r'\#{',
    comment_end_string='}',
    line_statement_prefix='%%',
    line_comment_prefix='%#',
    trim_blocks=True,
    autoescape=False,
    **kwargs)

def get_env():
    return _get_env(loader=FileSystemLoader(template_dir))
