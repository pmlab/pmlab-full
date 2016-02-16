#!/usr/bin/env python

import pyparsing as pp

_grammar = None

def _build_grammar():
    pp.ParserElement.setDefaultWhitespaceChars(" \t\n")
    place_statement = pp.Keyword("place") + pp.QuotedString('"')("name") + \
        pp.Optional(pp.Suppress("init") + pp.Word(pp.nums), default=0)("init")
    trans_statement = pp.Keyword("trans") + pp.QuotedString('"')("name") + \
        pp.Suppress("~") + pp.QuotedString('"')("event") + \
        pp.Optional(pp.Suppress("in") + pp.Group(pp.OneOrMore(pp.QuotedString('"')))("inputs")) + \
        pp.Optional(pp.Suppress("out") + pp.Group(pp.OneOrMore(pp.QuotedString('"')))("outputs"))
    statement = pp.Group(place_statement | trans_statement) + pp.Suppress(";")
    tpn = pp.OneOrMore(statement)
    tpn.ignore(pp.pythonStyleComment)

    return tpn

def _get_grammar():
    global _grammar
    if _grammar is None:
        _grammar = _build_grammar()
    return _grammar

def _clean_name(name):
    return str.decode(name, 'string_escape').strip()

def pn_from_tpn(file):
    from . import PetriNet

    if hasattr(file, 'name'):
        filename = file.name
    else:
        filename = str(file)

    pn = PetriNet(filename=filename, format='tpn')
    ast = _get_grammar().parseFile(file, parseAll=True)

    for l in ast:
        if l[0] == 'place':
            name = _clean_name(l.name)
            init = int(l.init[0])
            p = pn.add_place(name)
            pn.set_initial_marking(p, init)
        elif l[0] == 'trans':
            name = _clean_name(l.event)
            if "$invisible$" in name:
                name = _clean_name(l.name)
                dummy = True
            else:
                dummy = False
            pn.add_transition(name, dummy=dummy)

            for a in l.inputs:
                place = _clean_name(a)
                pn.add_edge(place, name)

            for a in l.outputs:
                place = _clean_name(a)
                pn.add_edge(name, place)
        else:
            raise ValueError, l[0]

    pn.to_initial_marking()
    return pn
