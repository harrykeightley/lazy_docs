"""
Stolen with love from Brae Webb.
"""

import re
from typing import Dict, Iterable, List
import pdoc
from docstring_parser import parse

def traverse(modules: Iterable[pdoc.Module]):
    for mod in modules:
        yield mod
        for submod in mod.submodules():
            yield from traverse(submod)
        
class Formatter(object):
    """Takes in a structure iterable and generates the appropriate formatted
    documentation"""
    
    def __init__(self, files: List[str], markers: Dict[str, str]) -> None:
        self._modules = files  # Public submodules are auto-imported
        self._markers = markers

        context = pdoc.Context()
        self._modules = [pdoc.Module(mod, context=context)
                for mod in self._modules]
        pdoc.link_inheritance(context)

        self._body = []

    def export(self, file):
        """Exports the documentation to the supplied file for a given format."""
        self._clear()
        self._build()
        with open(file, 'w') as outfile:
            outfile.write(self._format(self._body))

    def _clear(self):
        self._body = []

    def _format(self, body) -> str:
        """Formats and returns the built components stored in the body """
        raise NotImplementedError()

    def _build(self):
        for mod in traverse(self._modules):
            for clazz in mod.classes(sort=False):
                if clazz.name in self._markers:
                    self._add_marker(clazz.name)
                    
                self._add_class(clazz)
                all_methods = clazz.methods(include_inherited=False, sort=False)
                for method in all_methods:
                    self._add_method(method)

    def _add_marker(self, marker):
        raise NotImplementedError()

    def _add_class(self, clazz):
        raise NotImplementedError()
            
    def _add_method(self, method):
        raise NotImplementedError()


class MarkdownFormatter(Formatter):

    def _format(self, body) -> str:
        return '\n'.join(body)

    def _add_marker(self, marker):
        return

    def _add_class(self, clazz):
        self._body.append("# " + clazz.name)

        superclasses = [c.name for c in clazz.mro()]
        if len(superclasses) > 0:
            self._body.append(f"Inherits from `{superclasses[0]}`")

        class_doc = str(clazz.obj.__doc__)
        self._body.append(f"doc: {class_doc}")
            
    def _add_method(self, method):
        params = ", ".join(method.params(annotate=True))
        method_signature = _sanitize(method.name)
        method_signature += "(" + convert_type(params) + ")"
        method_signature += " -> " + convert_type(method.return_annotation())

        if method_signature.startswith("\_\_init\_\_"): # pylint: disable=(anomalous-backslash-in-string)
            method_signature = "Constructor"

        self._body.append(f"## `{method_signature}`")
        self._body.append(method.docstring)
        self._body.append('\n')


class DotFormatter(Formatter):
    NODE = 0
    EDGE = 1
    RANK = 2

    def _format(self, body) -> str:
        header = f'digraph "classes" {{\ncharset="utf-8"\nrankdir=BT\n' 

        body.sort(key=lambda x: (x[0], x[1]))
        body = "\n".join(message for code, message in self._body if code != self.RANK)

        origin_classes = (f'"{name}"' for code, name in self._body if code == self.RANK)
        body += f'\n{{ rank=same; {", ".join(origin_classes)} }}\n'

        return header + body + '}'

    def _build(self):
        for mod in traverse(self._modules):
            for clazz in mod.classes(sort=False):
                if clazz.name in self._markers:
                    self._add_marker(clazz.name)
                    
                self._add_class(clazz)
                all_methods = clazz.methods(include_inherited=False, sort=False)
                for method in all_methods:
                    self._add_method(method)

    def _add_marker(self, marker):
        return

    def _add_class(self, clazz):
        self._body.append((self.NODE, f'"{clazz.name}" [color=cyan3, label="{clazz.name}", shape="box"];'))
        superclasses = [c.name for c in clazz.mro()]
        if len(superclasses) > 0:
            superclass = superclasses[0]
            self._body.append((self.EDGE, f'"{clazz.name}" -> "{superclass}" [arrowhead="empty", arrowtail="none"];'))
        else:
            self._body.append((self.RANK, clazz.name))
            
    def _add_method(self, method):
        return


class LatexFormatter(Formatter):
    def _format(self, body) -> str:
        return '\n'.join(body)

    def _add_marker(self, marker):
        self._body.append("\\vspace{10mm}")
        self._body.append("\\subsection{" + self._markers[marker] + "}")
        self._body.append('\n')
        self._body.append("\\vspace{-12mm}")

    def _add_class(self, clazz):
        self._body.append("\\vspace{15mm}")
        self._body.append("\\classname{" + clazz.name + "}\\vspace{3mm}\\newline")

        superclasses = [c.name for c in clazz.mro()]
        if len(superclasses) > 0:
            self._body.append("\\textbf{Inherits from " + markup(superclasses[0]) + "}\\newline")

        class_doc = str(clazz.obj.__doc__)
        self._body.append(method_to_latex(class_doc))
            
    def _add_method(self, method):
        self._body.append("\\vspace{8mm}")
        params = ", ".join(method.params(annotate=True))
        method_signature = _sanitize(method.name)
        method_signature += "(" + convert_type(params) + ")"
        method_signature += " -> " + convert_type(method.return_annotation())

        if method_signature.startswith("\_\_init\_\_"): # pylint: disable=(anomalous-backslash-in-string)
            method_signature = "Constructor"

        self._body.append("\\methodname{" + method_signature + "}\\vspace{2mm}\\newline")
        self._body.append(method_to_latex(method.docstring))
        self._body.append('\n')
        

# ---------------- HELPERS --------------------

def _sanitize(text):
    return (text
        .replace("a2_support.", "")
        .replace("a2_solution.", "")
        .replace("_", "\_") # pylint: disable=(anomalous-backslash-in-string)
        .replace("#", "\#") # pylint: disable=(anomalous-backslash-in-string)
    )

def convert_type(type_rep):
    result = _sanitize(type_rep)
    # WARNING: the space before NoneType is not a real space, it's some bs
    result = re.sub(r'Union\[([^,]+?), NoneType\]', r'Optional[\1]', result)
    result = result.replace("NoneType", "None")
    return result

def sub(pattern, replacement, string):
    while True:
        result = re.sub(pattern, replacement, string)
        if result == string:
            break
        string = result
    return result

def markup(markdown):
    result = re.sub(r'`(.*)`', r'\\texttt{\1}', markdown)
    result = re.sub(r'_(.*)_', r'\\textsl{\1}', result)
    result = re.sub(r"'(.*)'", r"`\1'", result)

    result = _sanitize(result)

    return result

def parameters_to_latex(params):
    if len(params) <= 0:
        return ""

    items = "\\begin{itemize}\n"
    for param in params:
        items += "\\item \\texttt{" + param.arg_name + "}: " + param.description + "\n"
    items += "\\end{itemize}\n"

    return items

def examples_to_latex(example):
    examples = "\\textbf{Examples}\n"
    examples += "\\begin{example}\n"
    description = re.sub(r"\{", "\{", example.description)
    description = re.sub(r"\}", "\}", description)
    description = re.sub(r"'(.*)'", r"{\\textquotesingle}\1{\\textquotesingle}", description)
    examples += description + "\n"
    examples += "\\end{example}\n"
    return examples


def meta_to_latex(metas):
    latex = ""
    for meta in metas:
        if "examples" in meta.args:
            latex += examples_to_latex(meta)
    return latex


def method_to_latex(docstring):
    latex = ""
    docstring = canonicalize_description(docstring)
    doc = parse(docstring)
    
    # join descriptions
    description = doc.short_description
    if description is not None and doc.long_description is not None:
        description += "\n\n" + doc.long_description
    latex += markup(description)

    latex += "\n"
    latex += markup(parameters_to_latex(doc.params))

    latex += "\n\n"

    latex += meta_to_latex(doc.meta)

    return latex


def canonicalize_description(docstring):
    STOP_AT = {"Parameters:", "Examples:", "Raises:"}
    group = True
    block = ""
    in_list = False
    for line in docstring.split("\n"):
        if line.strip() in STOP_AT:
            group = False

        if group:
            if line == "":
                if in_list:
                    block += "\n\\end{itemize}"
                    in_list = False
                block += "\n\n"
                continue
            if line.strip().startswith("*"):
                if not in_list:
                    block += "\\begin{itemize}"
                    in_list = True
                block += "\n\\item" + line.replace("*", "").rstrip()
                continue
            
            block += " " + line.rstrip()
        else:
            block += line + "\n"
    return block