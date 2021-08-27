"""
Stolen with love from Brae Webb.
"""

import re
import sys
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

    def export(self):
        for mod in traverse(self._modules):
            for clazz in mod.classes(sort=False):
                if clazz.name in self._markers:
                    self.format_marker(clazz.name)
                    
                self.format_class(clazz)
                all_methods = clazz.methods(include_inherited=False, sort=False)
                for method in all_methods:
                    self.format_method(method)

    def format_marker(self, marker):
        raise NotImplementedError()

    def format_class(self, clazz):
        raise NotImplementedError()
            
    def format_method(self, method):
        raise NotImplementedError()


class LatexFormatter(Formatter):
    def format_marker(self, marker):
        print("\\vspace{10mm}")
        print("\\subsection{" + self._markers[marker] + "}")
        print()
        print("\\vspace{-12mm}")

    def format_class(self, clazz):
        print("\\vspace{15mm}")
        # class parsing
        print("\\classname{" + clazz.name + "}\\vspace{3mm}\\newline")

        superclasses = [c.name for c in clazz.mro()]
        if len(superclasses) > 0:
            print("\\textbf{Inherits from " + markup(superclasses[0]) + "}\\newline")

        class_doc = str(clazz.obj.__doc__)
        print(method_to_latex(class_doc))

        all_methods = clazz.methods(include_inherited=False, sort=False)
        for method in all_methods:
            self.format_method(method)
            
    def format_method(self, method):
        print("\\vspace{8mm}")
        params = ", ".join(method.params(annotate=True))
        method_signature = _sanitize(method.name)
        method_signature += "(" + convert_type(params) + ")"
        method_signature += " -> " + convert_type(method.return_annotation())

        if method_signature.startswith("\_\_init\_\_"): # pylint: disable=(anomalous-backslash-in-string)
            method_signature = "Constructor"

        print("\\methodname{" + method_signature + "}\\vspace{2mm}\\newline")
        
        print(method_to_latex(method.docstring))
        print()
        

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