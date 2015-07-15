# TODO Handle arcs with multiplicity > 1

def bound(pn):
    """Artificially creates new places in [pn] which ensure that every
    preexisting place will never contain more tokens than its capacity,
    even if the original [pn] is unbounded.
    This function does not do any intelligent analysis; the returned net will
    have twice the number of places of the original net."""
    places = pn.get_places(names = False)
    for p in places:
        capacity = pn.vp_place_capacity[p]
        if capacity <= 0:
            continue # No capacity limit, no constraint
        if p.in_degree() == 0:
            continue # No input degree, this place cannot get new tokens

        name = pn.vp_elem_name[p]
        marking = pn.vp_place_initial_marking[p]

        # QXXXXX will be the name of the place that constraints PXXXX
        if name.startswith('P'):
            qname = 'Q' + name[1:]
        elif name.startswith('p'):
            qname = 'q' + name[1:]
        else:
            qname = 'q_' + name

        q = pn.add_place(qname)
        pn.set_initial_marking(q, capacity - marking)
        pn.set_capacity(q, capacity - marking)

        for e in p.in_edges(): # Incoming edges
            t = e.source()
            if p in t.in_neighbours(): continue # Self-loop, skip it
            pn.add_edge(q, t)

        for e in p.out_edges():
            t = e.target()
            if p in t.out_neighbours(): continue # Self-loop, skip it
            pn.add_edge(t, q)

