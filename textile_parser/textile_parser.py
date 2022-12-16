from lark import Lark, Tree
from lark.visitors import Interpreter, visit_children_decor
from lark.lexer import Lexer, Token
from dataclasses import dataclass
import re
from . import latex_jinja
from os.path import join, realpath, dirname
import sys


dir = realpath(dirname(__file__))
grammar_file = join(dir, '../grammar.lark')

DEFAULT_LOCATION = "unknown"


def latex_encode(value):
    to_escape = r"([#&%])"
    return re.sub(to_escape, r"\\\1", value)


def transform_key(key):
    key = key.lower()
    match key:
        case "cvssv3vector":
            key = "cvss_vector"
        case "cvssv3.basescore" | "cvssv3.environmentalscore":
            key = "cvss_score"
    return key


@dataclass
class Footnote:
    index: int
    link: str


@dataclass
class FootnoteAnchor:
    index: int


@dataclass
class Evidence:
    location: str
    textile: str


@dataclass
class TableLine:
    text: str
    is_header: bool
    num_columns: int


class JinjaEnv(Interpreter):
    footnotes = {}

    def __init__(self, table_headers=True, table_newline="\\tnl"):
        self.table_headers = table_headers
        self.table_newline = table_newline
        super().__init__()

    @visit_children_decor
    def elements(self, elements):
        res = {}
        for e in elements:
            key, value = e
            res[transform_key(key)] = value
        return res

    @visit_children_decor
    def element(self, items):
        return items

    @visit_children_decor
    def field(self, items):
        return items[0]

    @visit_children_decor
    def field_name(self, items):
        return items[0]

    def content(self, tree):
        self.footnotes = {} 

        # Get all footnotes
        for item in tree.iter_subtrees():
            if item.data == "footnote":
                index, link = self.visit(item)
                self.footnotes[index] = link

        # Parse the rest
        output = []
        for item in tree.children:
            item = self.visit(item)
            item = item.strip()
            # Check if item was not only newline/whitespace
            if item:
                output.append(item)
        return "\n\n".join(output)

    def paragraph(self, tree):
        output = []
        for item in tree.children:
            if not isinstance(item, Tree):
                continue
            if item.data == "footnote":
                # Footnotes have already been parsed at this point
                continue
            output.append(self.visit(item))
        return "".join(output)

    @visit_children_decor
    def table(self, items):
        separator = " {}\n".format(self.table_newline)
        table_content = []
        columns_descriptor = None
        i = 0
        header = ""
        for item in items:
            if hasattr(item, 'type') and item.type == "TABLE_CAPTION_TEXT":
                # Don't do anything with the caption at the moment
                continue
            if i == 0:
                columns_descriptor = "|" + "L|"*(item.num_columns-1) + "L|"
                if item.is_header:
                    header = "\\theadstart\n" + item.text + separator
            else:
                # Add normal lines
                table_content.append(item.text)
            i += 1
        table_content = separator.join(table_content) + separator
        if self.table_headers:
            return f"""\
                \\begin{{tabulary}}{{\\textwidth}}{{{columns_descriptor}}}
                    {header}
                    \\tbody
                    {table_content}
                    \\tend
                \\end{{tabulary}}"""
        else:
            return table_content

    @visit_children_decor
    def table_caption(self, items):
        # Return the caption text
        return items[1]

    @visit_children_decor
    def table_line(self, items):
        is_header = False
        output = []
        for item in items:
            if not item.type == "TABLE_TEXT":
                continue
            if item.startswith("_."):
                # Table header
                item = "\\thead " + item[2:]
                is_header = True
            output.append(item)
        return TableLine(
            " & ".join(output),
            is_header,
            num_columns = len(output))

    @visit_children_decor
    def paragraph_line(self, items):
        output = []
        for item in items:
            if hasattr(item, 'type') and item.type == "FOOTNOTE_ANCHOR":
                item = self.FOOTNOTE_ANCHOR(item)
            else:
                item = latex_encode(item)
            output.append(item)
        return "".join(output)

    @visit_children_decor
    def code_block(self, items):
        items = filter(lambda x: x.type != "CODE_BLOCK_START", items)
        return r"\begin{code}" + "\n" + "".join(items) + r"\end{code}"

    @visit_children_decor
    def inline_code_block(self, items):
        items = filter(lambda x: x.type != "INLINE_CODE_BLOCK_START", items)
        return r"\begin{code}" + "\n" + "".join(items) + r"\end{code}"

    @visit_children_decor
    def bullets(self, items):
        return r"\begin{itemize}" + "\n" + ''.join(items) + r"\end{itemize}" + "\n"

    @visit_children_decor
    def enumeration(self, items):
        return r"\begin{enumerate}" + "\n" + ''.join(items) + r"\end{enumerate}" + "\n"

    @visit_children_decor
    def bullet(self, items):
        return r"\item " + items[1]

    item = bullet

    def FOOTNOTE_ANCHOR(self, item):
        m = re.match(r"<(\d)>", item)
        footnote_index = m.group(1)
        try:
            footnote_text = self.footnotes[footnote_index]
        except KeyError:
            raise Exception("No footnote found for anchor: <{footnote_index}>.")
        return r"\footnote{" + latex_encode(footnote_text) + "}"

    @visit_children_decor
    def bold_text(self, items):
        return r"\textbf{" + latex_encode(items[1]) + "}"

    @visit_children_decor
    def italics_text(self, items):
        return r"\textit{" + latex_encode(items[1]) + "}"

    @visit_children_decor
    def monospace_text(self, items):
        return r"\texttt{" + latex_encode(items[0]) + "}"

    @visit_children_decor
    def footnote(self, items):
        m = re.match(r"bc\.\.? fn(\d). ", items[0])
        index = m.group(1)
        return index, items[1]


def parse_textile(textile, **kwargs):
    # Ensure that file ends with a newline
    if textile[-1] != "\n":
        textile += "\n"
    tree = parser.parse(textile)
    return JinjaEnv(**kwargs).visit(tree)


def evidence_content(evidence):
    content = parse_textile(evidence.textile)
    if not hasattr(content, 'location'):
        content['location'] = evidence.location or DEFAULT_LOCATION
    return content


def check_issue(content):
    # Perform some checks on the validity of the issue.
    # Currently does nothing
    pass

def issue_content(issue, evidences=[]):
    content = parse_textile(issue)
    check_issue(content)
    content['evidences'] = [evidence_content(e) for e in evidences]
    return content


def render_issue(content):
    env = latex_jinja.get_env()
    issue_template = env.get_template("issue.tex")
    return issue_template.render(content)


def issue_to_latex(issue, evidences=[]):
    content = issue_content(issue, evidences)
    return render_issue(content)


def read_file(filename):
    with open(filename) as f:
        return f.read()


def parse_textile_file(filename):
    try:
        return parse_textile(read_file(filename))
    except Exception as e:
        print(f"Exception while parsing {filename}:", file=sys.stderr)
        raise e


def issue_files_to_latex(issue_file, evidence_files=[], evidence_locations=[]):
    issue = read_file(issue_file)
    evidence_textiles = map(read_file, evidence_files)
    evidences = []
    if evidence_locations:
        for textile, location in zip(evidence_textiles, evidence_locations):
            evidences.append(Evidence(location, textile))
    else:
        for textile in evidence_textiles:
            evidences.append(Evidence(None, textile))
    return issue_to_latex(issue, evidences)


grammar = read_file(grammar_file)
parser = Lark(grammar, parser='lalr', start='elements')


def main():
    import argparse
    import sys
    argparser = argparse.ArgumentParser(description="Convert Dradis issues to latex")
    argparser.add_argument("issue_file")
    argparser.add_argument("-e", "--evidence_files", nargs='*', default=[])
    argparser.add_argument("-l", "--evidence_locations", nargs='*', default=[], help="The hosts or locations where the issue exists (zipped with evidence files, must be same length)")
    args = argparser.parse_args()
    if args.evidence_locations and len(args.evidence_files) != len(args.evidence_locations):
        print("Please ensure that a location is provided for each evidence")
        sys.exit()

    latex_issue = issue_files_to_latex(args.issue_file, args.evidence_files, args.evidence_locations)
    print(latex_issue)


if __name__ == "__main__":
    main()
