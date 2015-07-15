"""Module to encode the C-net discovery problem into a SAT problem using
Satisfiability Modulo Theories (SMT). Ouput is a CVC file (to stdout)
which can be fed to the STP solver."""
from collections import defaultdict, namedtuple
from operator import itemgetter
#from optparse import OptionParser, OptionGroup
import itertools
import bisect
#import cnet

VariableInformation = namedtuple('VariableInformation','alphabet variables obligation_dict input_alphabet output_alphabet')

def constant_factory(value):
    return itertools.repeat(value).next

def binary(number, digits=8):
    """Returns the binary string that represents [n] with the given 
    number of [digits]."""
    return "{0:0>{1}}".format(bin(number)[2:], digits)

def sum_of_bits( bit_list, digits=None, use_parenthesis=False ): 
    """Returns the STP expression that represents the sum of an iterable 
    representing bits. If [digits] is None, the size of the sum is determined by
    the number of elements in [bit_list]."""
    if digits == None:
        bits = len(bin(len(bit_list)))-2 # -2 because of '0b' prefix
    else:
        bits = digits
    if len(bit_list) == 1:
        if bits == 1:
            return bit_list[0]
        return "0bin"+'0'*(bits-1)+'@'+bit_list[0]
    if use_parenthesis:
        left_separator = '('
        right_separator = ')'
    else:
        left_separator = ''
        right_separator = ''
    return "BVPLUS({0},".format(bits)+','.join(["0bin"+'0'*(bits-1)+'@'+
        left_separator+bool_var+right_separator for bool_var in bit_list])+')'

def var_prefix( case_num, index ): # trace, 
    """Returns the Boolean variable prefix for a given trace at 
    position [index]"""
    return "t{0}".format( case_num ) # use trace number otherwise

def boolean_variables(traces, activity_window=0, exclusive_use_arcs=None, 
                    ignored_arcs=None, add_ignored_arcs_to_window=True):
    """Returns the set of Boolean variables used to encode the problem.
    
    By default considers all possible activity combinations, except if either
    [activity_window] > 0 or [exclusive_arcs] is a non-empty list. Both
    conditions can hold at the same time (so that all the relations in 
    [exclusive_arcs] plus the ones in the activity window are considered.
    """
    exclusive_arcs = exclusive_use_arcs if exclusive_use_arcs else []
    ignore_arcs = ignored_arcs if ignored_arcs else []
    input_alphabet = defaultdict(set)
    output_alphabet = defaultdict(set)
    check_alphabet = (activity_window > 0) or (len(exclusive_arcs) > 0)
    if check_alphabet:
        for act1, act2 in exclusive_arcs:
            input_alphabet[act2].add( act1 )
        # check if ignored arcs have to be added to the alphabets
        if add_ignored_arcs_to_window:
            for act1, act2 in ignore_arcs:
                input_alphabet[act2].add( act1 )
        # compute activity alphabets
        if activity_window > 0:
            for words in traces:
                # compute input alphabet
                for i, w in enumerate(words):
                    for j in range(i-activity_window, i):
                        input_alphabet[w].add( words[j] )
        else:
            # sanity check: ensure that all non-initial activities have at least one possible predecessor
            initial_act = traces.keys()[0][0]
#            repair_pre = set()
#            for act1, act_set in input_alphabet.iteritems():
#                if act1 != initial_act and len(act_set) == 0:
#                    print "% the use of exclusive arcs prevented a necessary predecessor for {0}, using window of size 1 for that activity".format( act1 )
#                    repair_pre.add( act1 )
            #unfortunately this check is not enough, we must guarantee that the activity has a predecessor 
            #in EACH sequence in the log
            for case_num, words in enumerate(traces):
                seen_alph = set()
                for i, w in enumerate(words):
                    if w == initial_act:
                        seen_alph.add(w)
                        continue
                    feasible_pred = seen_alph & input_alphabet[w]
                    seen_alph.add(w)
                    if len(feasible_pred) == 0:
                        #add immediate predecessor
                        print ("%The use of exclusive arcs prevented a necessary"
                            " predecessor for {0} in seq {1}, using immediate "
                            "predecessor for that activity ({2})").format( w, 
                                                                            case_num,
                                                                            words[i-1])
                        input_alphabet[w].add( words[i-1] )
                                            
        # compute also output alphabet, by reversing information
        for act1, act_set in input_alphabet.iteritems():
            for act2 in act_set:
                output_alphabet[act2].add(act1)
        if activity_window == 0:
            # sanity check: ensure that all non-final activities have at least one possible successor
            final_act = traces.keys()[0][-1]
#                repair_post = set()
#                for act1, act_set in output_alphabet.iteritems():
#                    if act1 != final_act and len(act_set) == 0:
#                        print "% the use of exclusive arcs prevented a necessary successor for {0}, using window of size 1 for that activity".format( act1 )
#                        repair_post.add( act1 )
#                if (len(repair_post) > 0):
#                    for words in traces:
#                        # compute input alphabet
#                        for i, w in enumerate(words):
#                            if w not in repair_pre: 
#                                continue
#                            for j in range(i+1, i+2):
#                                output_alphabet[w].add( words[j] )
#                                # to keep consistency
#                                input_alphabet[words[j]].add( w )
            ##check output consistency at the same detail level than done with input before.
            for case_num, words in enumerate(traces):
                for i, w in enumerate(words):
                    if w == final_act:
                        continue
                    #not optimal, but for the moment will do
                    feasible_succ = set(words[i+1:]) & output_alphabet[w]
                    if len(feasible_succ) == 0:
                        #add immediate predecessor
                        print ("%The use of exclusive arcs prevented a necessary"
                            "successor for {0} in seq {1}, using immediate "
                            "predecessor for that activity ({2})").format( w, 
                                                                            case_num, 
                                                                            words[i+1])
                        output_alphabet[w].add( words[i+1] )
                        #update also input alphabet
                        input_alphabet[words[i+1]].add( w )
                            
    variables = []
    obligation_dict = {}
    alphabet = set()
    # maps each obligation (a,b) to a tuple: 
    # (0) variables for input (1) variables for output
    for case_num, words in enumerate(traces):
        for i in range(len(words)):
            alphabet.add( words[i] )
            #input variables (obligation consumption)
            seen_vars = set()
            for j in range(i):
                if check_alphabet and words[j] not in input_alphabet[words[i]]:
                    continue
                if words[j] not in seen_vars:
                    var_name = "{0}x{1}_{2}_{3}".format(
                                    var_prefix( case_num, i), i, 
                                    words[j], words[i])
                    if (words[j], words[i]) not in obligation_dict:
                        obligation_dict[(words[j], words[i])] = ([var_name], [])
                    else:
                        obligation_dict[(words[j], words[i])][0].append(var_name)
                    seen_vars.add( words[j] )
                    variables.append( var_name )
            #output variables (obligation production)            
            seen_vars = set()
            for j in range(i+1, len(words)):
                if check_alphabet and words[j] not in output_alphabet[words[i]]:
                    continue
                if words[j] not in seen_vars:
                    var_name = "{0}y{1}_{2}_{3}".format(
                                var_prefix(case_num, j), i, 
                                words[i], words[j])
                    if (words[i], words[j]) not in obligation_dict:
                        obligation_dict[(words[i], words[j])] = ([], [var_name])
                    else:
                        obligation_dict[(words[i], words[j])][1].append(var_name)
                    seen_vars.add( words[j] )
                    variables.append( var_name )
#    if options.max_input_sets > 0 or len(options.explicit_max_input_sets) > 0:
#        max_input_sets = defaultdict(constant_factory(int(options.max_input_sets)))
#        for act, limit in options.explicit_max_input_sets:
#            max_input_sets[act] = limit
#        #print max_input_sets
#        # add insets auxiliary variables
#        for act1, act2 in obligation_dict:
#            #print 'activity', act2, 'limit', max_input_sets[act2]
#            for i in range(int(max_input_sets[act2])):
#                var_name = "_i{0}_{1}_{2}".format( i, act1, act2)
#                variables.append( var_name )
#    if options.max_output_sets > 0:
#        # add insets auxiliary variables
#        for act1, act2 in obligation_dict:
#            for i in range(options.max_output_sets):
#                var_name = "_o{0}_{1}_{2}".format( i, act1, act2)
#                variables.append( var_name )
    return VariableInformation( alphabet, variables, obligation_dict, input_alphabet, output_alphabet )

#def build_seq_ts( traces ):
#    """Builds the sequential TS of the given log stored in [traces_seen]. 
#    Must be called after load_log."""
#    seq_ts = TransitionSystem()
#    for words, trace_info in traces.iteritems():
#        seq_ts.reset_state()
#        trace_number = trace_info[0]
#        for i in range(len(words)):
#            seq_ts.set_state( seq_ts.add_transition( seq_ts.state(), words[i], 
#                                                    trace_number, 
#                                                    trace_info[1] ) )
#        seq_ts.add_trace_info( seq_ts.state(), trace_info[0], trace_info[1] )
#    return seq_ts

#def generate_penalties_for_early_enabling( seq_ts ):
#    pass

def generate_structural_stp_inout( log, var_info ):
    """Prints the structural constraints that guarantee that the result 
    corresponds to a C-net that includes the traces (any valid C-net including 
    it has to satisfy these equations). Uses both input and output Boolean 
    variables for the encoding."""
    traces = log.get_uniq_cases()
    activity_positions = log.get_activity_positions()
    if len(var_info.input_alphabet) > 0:
        check_alphabet = True
        input_alphabet = var_info.input_alphabet
        output_alphabet = var_info.output_alphabet
    else:
        check_alphabet = False
    constraint_number = 0
    for case_num, words in enumerate(traces):
        for i in range(len(words)):
            positions_i = activity_positions[case_num][words[i]]
            all_past_positions_i = positions_i[:positions_i.index(i)+1]
            #print "positions_i:", positions_i, 
            #print "positions_i.index(i):", positions_i.index(i)
            #print "i:", i, "all_past_positions_i:", all_past_positions_i
            #input variables (obligation consumption)
            input_vars = []
            for j in range(i):
                if check_alphabet and words[j] not in input_alphabet[words[i]]:
                    continue
                positions_j = activity_positions[case_num][words[j]]
                if positions_j[0] == j:
                    var_name_i = "t{0}x{1}_{2}_{3}".format(case_num, i, 
                                                            words[j], words[i])
                    input_vars.append( var_name_i )
                    #be careful: results cannot precede causes and an occurrence
                    # cannot be cause of itself so the past positions of i have
                    # to be greater than the first past position of j
                    past_positions_j = positions_j[:bisect.bisect_left(positions_j, i)] 
                    # positions p of j s.t. p < i
                    past_positions_i = all_past_positions_i[bisect.bisect_right(all_past_positions_i, past_positions_j[0]):]
                    #print "j:", j, "past_positions_j", past_positions_j
                    #print "past_positions_i", past_positions_i
                    if len(past_positions_i) == len(past_positions_j) == 1:
                        var_name_j = "t{0}y{1}_{2}_{3}".format(case_num, j,
                                                                words[j], 
                                                                words[i])
                        if positions_i[-1] == i: 
                            # it is the last execution of activity i
                            print "ASSERT("+var_name_j+'='+var_name_i+");"
                        else:
                            print "ASSERT("+var_name_j+'|~'+var_name_i+"=0bin1);"
                        constraint_number += 1
                    else: # use arithmetic expression
                        var_names_i = ["t{0}x{1}_{2}_{3}".format(case_num, k, words[j], words[i]) 
                                        for k in past_positions_i]
                        var_names_j = ["t{0}y{1}_{2}_{3}".format(case_num, k, words[j], words[i]) 
                                        for k in past_positions_j]
                        max_value = max(len(past_positions_i), 
                                        len(past_positions_j))
                        #compute required number of bits
                        bits = len(bin(max_value))-2 
                        # -2 because of '0b' prefix
                        last_execution = (past_positions_i[-1] == positions_i[-1])
                        if last_execution: # it is the last execution of act. i
                            constraint = ("ASSERT("+
                                sum_of_bits( var_names_j, bits )+'='+
                                sum_of_bits( var_names_i, bits )+');')
                        else: 
                            constraint = ("ASSERT(BVGE("+
                                sum_of_bits( var_names_j, bits )+','+
                                sum_of_bits( var_names_i, bits )+'));')
                        print constraint
                        constraint_number += 1
            if len(input_vars) > 0:
                print "ASSERT("+"|".join(input_vars)+"=0bin1);"
                constraint_number += 1
            else:
                if i > 0:
                    print ("% System unfeasible due to lack of suitable "
                            "predecessors in sequence {0} position {1}").format( case_num, i )
                    print "ASSERT(FALSE);"
                    constraint_number += 1
            output_vars = []
            for j in range(i+1, len(words)):
                if check_alphabet and words[j] not in output_alphabet[words[i]]:
                    continue
                positions_j = activity_positions[case_num][words[j]]
                if positions_j[-1] == j:
                    var_name = "t{0}y{1}_{2}_{3}".format(case_num, i, 
                                words[i], words[j])
                    output_vars.append( var_name )
            if len(output_vars) > 0:
                print "ASSERT("+"|".join(output_vars)+"=0bin1);"
                constraint_number += 1
            else:
                if i < len(words)-1:
                    print ("% System unfeasible due to lack of suitable "
                            "successors in sequence {0} position {1}").format( case_num, i )
                    print "ASSERT(FALSE);"
                    constraint_number += 1
    return constraint_number

def generate_stp_avoid_binding_seq( log, var_info, 
                                    binding_seq, options ):
    """Print equations to forbid a set of binding sequences, by forbidding
    at least one binding of each sequence."""
    traces = log.get_uniq_cases()
    activity_positions = log.get_activity_positions()
    if len(var_info.input_alphabet) > 0:
        check_alphabet = True
        input_alphabet = var_info.input_alphabet
        output_alphabet = var_info.output_alphabet
    else:
        check_alphabet = False
    if len(binding_seq) == 0:
        return 0
    print '% Equations forbidding {0} wrong binding sequences'.format( len(binding_seq) )
    constraint_number = len(binding_seq)
    for seq in binding_seq:
        ibindings = set()
        obindings = set()
        for bind in seq:
            ibindings.add( (bind[0],frozenset(bind[1])) )
            obindings.add( (bind[0],frozenset(bind[2])) )
        final_list = []
        for binding in ibindings:
            event = binding[0]
            and_list = []
            for case_num, words in enumerate(traces):
                for pos in activity_positions[trace_number][event]:
                    available = (set(words[:pos]) & input_alphabet[event] 
                                if check_alphabet else set(words[:pos]))
                    if binding[1] > set() and binding[1] <= available: # we have to restrict
                        or_term = '('+'&'.join(['{0}x{1}_{2}_{3}'.format(
                                    var_prefix(case_num, pos), pos, act, event)
                                    for act in binding[1]])+')=0bin0'
                        remainder = available-binding[1]
                        if len(remainder) > 0:
                            or_term += ' OR ('+'|'.join(['{0}x{1}_{2}_{3}'.format(
                                    var_prefix(case_num, pos), pos, act, event)
                                    for act in remainder])+')=0bin1'
                        and_list.append( or_term )
    #                    print and_list
            and_term = ' AND '.join(['({0})'.format(or_term) for or_term in and_list])
            if len(and_term) > 0:
                final_list.append( and_term )
        for binding in obindings:
            event = binding[0]
            and_list = []
            for case_num, words in enumerate(traces):
                for pos in activity_positions[trace_number][event]:
                    available = (set(words[pos+1:]) & output_alphabet[event] 
                                if check_alphabet else set(words[pos+1:]))
                    if binding[1] > set() and binding[1] <= available: # we have to restrict
                        or_term = '('+'&'.join(['{0}y{1}_{2}_{3}'.format(
                                    var_prefix(case_num, pos), pos, event, act)
                                    for act in binding[1]])+')=0bin0'
                        remainder = available-binding[1]
                        if len(remainder) > 0:
                            or_term += ' OR ('+'|'.join(['{0}y{1}_{2}_{3}'.format(
                                    var_prefix(case_num, pos), pos, event, act)
                                    for act in remainder])+')=0bin1'
                        and_list.append( or_term )
    #                    print and_list
            and_term = ' AND '.join(['({0})'.format(or_term) for or_term in and_list])
            if len(and_term) > 0:
                final_list.append( and_term )
        print 'ASSERT( {0} );'.format(' OR '.join(final_list))
    return constraint_number

def generate_stp_max_obligations(variables, max_global_obligations):
    """Print an equation that limits the amount of obligations used to simulate
    all traces. Uses only the input variables."""
    if max_global_obligations <= 0:
        return 0
    print "% Equations limiting complexity"
    obligation_bound = max_global_obligations
    print "% limiting the total number of obligations to", obligation_bound
    bits = len(bin(len(variables)))-2
    print ("ASSERT(BVLE("+sum_of_bits(variables)+
            ",0bin"+binary(obligation_bound, bits)+"));")
    return 1 # only 1 new constraint

def generate_stp_max_arcs(obligation_dict, max_global_arcs, ignored_arcs=None):
    """Print an equation that limits the amount of arcs in the resulting C-net.
    Uses only the input variables. Returns the number of constraints 
    generated"""
    if max_global_arcs <= 0 and not ignored_arcs == 0:
        return 0
    #if we have ignored arcs, 0 is a valid possibility 
    ignore_arcs = ignored_arcs if ignored_arcs else []
    #print ignored_arcs
    print "% Equations limiting complexity"
    print "% limiting total number of arcs to", max_global_arcs
    arcs = len(obligation_dict)
    bits = len(bin(arcs))-2
    to_sum = ['('+"|".join(sets[0])+')' 
                for obligation, sets in obligation_dict.iteritems() 
                if len(sets[0]) > 0 and obligation not in ignore_arcs]
    print ("ASSERT(BVLE("+sum_of_bits(to_sum, bits)+
            ",0bin"+binary(max_global_arcs, bits)+"));")
    return 1 # only 1 new constraint

#def generate_stp_max_enablings( traces, seq_ts, options ):
#    """Print an equation that limits the amount of early enablings in the 
#    resulting C-net."""
#    only_first_enabling = (options.max_early_first_enablings >= 0)
#    max_early_enablings = options.max_early_first_enablings
#    if max_early_enablings < 0:
#        return 0
#    print "% Equations limiting complexity"
#    print "% limiting total number of early enablings to", max_early_enablings
#    if seq_ts == None:
#        raise ValueError("Sequential TS must be defined")
#    if options.enabling_mode == 'roe':
#        seq_ts.compute_last_enablings()
#    elif options.enabling_mode == 'rod':
#        seq_ts.compute_last_enablings2()
#    #seq_ts.print_ts()
#    sumands = []
#    for words, trace_info in traces .iteritems():
#        #trace_number = trace_info[0]
#        seq_ts.reset_state()
#        seen_words = set()
#        for i in range(len(words)):
#            state = seq_ts.state()
#            seq_ts.set_state( seq_ts.follow_transition( seq_ts.state(), 
#                                                        words[i] ) )
#            forbidden_vars = []
#            enabling_point = seq_ts.last_enabling_for( state, words[i] )
#            if enabling_point == 0 or (only_first_enabling and words[i] in seen_words):
#                continue
#            seen_words.add( words[i] )
#            for j in range(enabling_point-1, i):
#                var_name = "(~{0}x{1}_{2}_{3})".format(
#                                var_prefix(trace_info, i), i, 
#                                words[j], words[i])
#                forbidden_vars.append( var_name )
#            sumands.append('&'.join(forbidden_vars))
#    bits = len(bin(max(len(sumands), max_early_enablings)))-2
#    print ("ASSERT(BVLE("+sum_of_bits(sumands, bits, use_parenthesis=True)+
#        ',0bin'+binary(max_early_enablings, bits)+'));')
#            #print "Forbidden for trace", words,"at",i,forbidden_vars
#    return 1 # only 1 new constraint
#
#def generate_stp_max_ttl( traces, max_ttl ):
#    """Print an equation that limits the amount of time that obligations are 
#    alive in the resulting C-net."""
#    if max_ttl < 0:
#        return 0
#    print "% Equations limiting complexity"
#    print "% Limiting total number of alive time for obligations to", max_ttl
#    #each activity in position i, can add up to i to sum
#    # thus each trace can contribute, at most, n(n-1)/2 where n=len(trace)
#    max_total = sum([len(t)*(len(t)-1)/2 for t in traces])
#    print "% Maximum possible ttl:", max_total
#    bits = len(bin(max(max_total, max_ttl)))-2
#    sumands = []
#    #compute max length of traces, since all 
#    for words, trace_info in traces.iteritems():
#        #trace_number = trace_info[0]
#        for i in range(len(words)):
#            for j in range(i-1):
#                forbidden_vars = []
#                pos_var_name = "{0}x{1}_{2}_{3}".format(
#                                var_prefix(trace_info, i), i, 
#                                words[j], words[i])
#                forbidden_vars.append( pos_var_name )
#                for k in range(j+1,i):
#                    var_name = "(~{0}x{1}_{2}_{3})".format(
#                                var_prefix(trace_info, i), i, 
#                                words[k], words[i])
#                    forbidden_vars.append( var_name )
#                sumands.append('BVSX('+'&'.join(forbidden_vars)+
#                                ',{0})&0bin{1}'.format(bits,binary(i-j-1,bits)))
#    print ("ASSERT(BVLE("+'BVPLUS({0},'.format(bits)+','.join(sumands)+')'
#        ',0bin'+binary(max_ttl, bits)+'));')
#            #print "Forbidden for trace", words,"at",i,forbidden_vars
#    return 1 # only 1 new constraint

#def generate_stp_max_input_sets( traces, var_info, max_input_sets ):
#    """Print an equation that limits the amount of input bindings per activity 
#    in the resulting C-net."""
#    if len(max_input_sets) == 0:
#        return 0
#    obligation_dict = var_info.obligation_dict
#    if len(var_info.input_alphabet) > 0:
#        check_alphabet = True
#        input_alphabet = var_info.input_alphabet
#    else:
#        check_alphabet = False
#    #print "% Equations limiting complexity"
#    # for each activity having an input set, compute the alphabet of activities in insets
#    ins_alphabet = defaultdict(set)
#    for act1, act2 in obligation_dict:
#        ins_alphabet[act2].add(act1)
#    #print ins_alphabet
#    #print max_input_sets
#    prefixes_seen = set()
#    final_list = []
#    for act, limit in max_input_sets.iteritems():
#        if limit > 0:
#            print "% limiting maximum number of input sets for '{0}' to".format(act), limit
#    for words, trace_info in traces.iteritems():
#        current_alphabet = set()
#        for i in range(len(words)):
#            prefix = "{0}x{1}".format(var_prefix(trace_info, i), i)
#            if prefix in prefixes_seen:
#                print "prefix",prefix,"found in", prefixes_seen 
#                #already added equation (useful for var_mode=input_state)
#                continue
#            prefixes_seen.add( prefix )
#            or_list = []
#            for k in range(max_input_sets[words[i]]):
#                in_and_list = []
#                for j in range(i):
#                    if check_alphabet and words[j] not in input_alphabet[words[i]]:
#                        continue
#                    in_vname = "_i{0}_{1}_{2}".format( k, words[j], words[i])
#                    var_name = "{0}_{1}_{2}".format( prefix, words[j], words[i])
#                    in_and_list.append( '('+var_name+'='+in_vname+')' )
#                #assign to 0 missing obligations
#                for act in ins_alphabet[words[i]] - current_alphabet:
#                    in_vname = "_i{0}_{1}_{2}".format( k, act, words[i])
#                    in_and_list.append( '('+in_vname+'=0bin0)' )
#                if len(in_and_list) > 0:
#                    or_list.append('('+' AND '.join( in_and_list )+')')
#            if len(or_list) > 0:
#                final_list.append( '('+' OR '.join( or_list )+')' )
#            current_alphabet.add( words[i])
#    if len(final_list) > 0:
#        print 'ASSERT('+' AND '.join(final_list)+');'
#        return 1 # only 1 new constraint
#    return 0
#
#def generate_stp_max_output_sets( traces, var_info, max_output_sets ):
#    """Print an equation that limits the amount of output bindings per activity 
#    in the resulting C-net."""
#    if len(max_output_sets) == 0:
#        return 0
#    obligation_dict = var_info.obligation_dict
#    if len(var_info.output_alphabet) > 0:
#        check_alphabet = True
#        output_alphabet = var_info.output_alphabet
#    else:
#        check_alphabet = False
##    print "% Equations limiting complexity"
##    print "% Limiting maximum number of output sets per activity to", max_output_sets
#    for act, limit in max_output_sets.iteritems():
#        if limit > 0:
#            print "% limiting maximum number of output sets for '{0}' to".format(act), limit
#    # for each activity having an output set, compute the alphabet of activities in outsets
#    outs_alphabet = defaultdict(set)
#    for act1, act2 in obligation_dict:
#        outs_alphabet[act1].add(act2)
#    #print outs_alphabet
#    prefixes_seen = set()
#    final_list = []
#    for words, trace_info in traces .iteritems():
#        #current_alphabet = set()
#        for i in range(len(words)):
#            current_alphabet= set( words[i+1:] )
#            prefix = "{0}y{1}".format(var_prefix(trace_info, i), i)
#            if prefix in prefixes_seen:
#                print "prefix",prefix,"found in", prefixes_seen 
#                #already added equation (useful for var_mode=input_state)
#                continue
#            prefixes_seen.add( prefix )
#            or_list = []
#            for k in range(max_output_sets[words[i]]):
#                out_and_list = []
#                for j in range(i+1,len(words)):
#                    if check_alphabet and words[j] not in output_alphabet[words[i]]:
#                        continue
#                    out_vname = "_o{0}_{1}_{2}".format( k, words[i], words[j])
#                    var_name = "{0}_{1}_{2}".format( prefix, words[i], words[j])
#                    out_and_list.append( '('+var_name+'='+out_vname+')' )
#                #assign to 0 missing obligations
#                for act in outs_alphabet[words[i]] - current_alphabet:
#                    out_vname = "_o{0}_{1}_{2}".format( k, words[i], act )
#                    out_and_list.append( '('+out_vname+'=0bin0)' )
#                if len(out_and_list) > 0:
#                    or_list.append('('+' AND '.join( out_and_list )+')')
#            if len(or_list) > 0:
#                final_list.append( '('+' OR '.join( or_list )+')' )
##            current_alphabet.add( words[i])
#    if len(final_list) > 0:
#        print 'ASSERT('+' AND '.join(final_list)+');'
#    return 1 # only 1 new constraint
#
#def generate_stp_min_equal_input_sets( traces, var_info, max_input_sets, min_bound ):
#    """Print an equation that limits the minimum amount of equal input bindings
#    in the log."""
#    if min_bound <= 0:
#        return 0
#    obligation_dict = var_info.obligation_dict
#    print "% Equations limiting complexity"
#    # for each activity having an input set, compute the alphabet of activities in insets
#    ins_alphabet = defaultdict(set)
#    for act1, act2 in obligation_dict:
#        ins_alphabet[act2].add(act1)
#    sumands = []
#    max_possible_value = 0
#    for act1 in ins_alphabet:
#        bound = max_input_sets[act1]
#        if bound == 0:
#            continue
#        
#        for i in range(bound):
#            for j in range(i+1,bound):
#                equality_list = []
#                for act2 in ins_alphabet[act1]:
#                    in1_vname = "_i{0}_{1}_{2}".format( i, act2, act1)
#                    in2_vname = "_i{0}_{1}_{2}".format( j, act2, act1)
#                    equality = '~BVXOR('+in1_vname+','+in2_vname+')'
#                    equality_list.append( equality )
#                if len(equality_list) > 0:
#                    sumands.append('('+'&'.join( equality_list )+')')
#        max_possible_value += bound*(bound-1)/2
#    if max_possible_value <= min_bound:
#        print '% max possible value for input binding equality is', max_possible_value,
#        print 'so minimum bound is changed from', min_bound, 'to', max_possible_value
#        min_bound = max_possible_value
#    print '% limiting minimum number of equal input sets to', min_bound,'(max is {0})'.format( max_possible_value )
#    bits = len(bin(max_possible_value))-2
#    
#    if len(sumands) > 0:
#        print 'ASSERT(BVGE('+sum_of_bits(sumands,bits)+',0bin'+binary(min_bound, bits)+'));'
#        return 1 # only 1 new constraint
#    return 0

def generate_stp_from_log( log, var_info, 
                            max_global_obligations=0, max_global_arcs=0,
                            #max_input_sets=0, max_output_sets=0,
                            ignore_arcs=None, binding_seq=None):
    """Main function to generate a CVC file (to stdout) that represents the 
    C-net discovery problem. The file can then be fed to the STP solver."""
    #print the variables
    traces = log.get_uniq_cases()
    activity_positions = log.get_activity_positions()
    #activity_positions = log_info.activity_positions
    variables = var_info.variables
    obligation_dict = var_info.obligation_dict
    print "% Total number of variables:", len(variables)
    for i in xrange(0,len(variables),10):
        print ','.join(variables[i:i+10]),': BITVECTOR(1);'
    #build the constraints
    constraint_number = generate_structural_stp_inout(log, var_info)

    print "% Structural constraints:", constraint_number
    constraint_number += generate_stp_max_obligations(variables, 
                                                        max_global_obligations)
    constraint_number += generate_stp_max_arcs(obligation_dict, 
                                                max_global_arcs, ignore_arcs)
    #constraint_number += generate_stp_max_enablings( traces, seq_ts, options )
    
    #constraint_number += generate_stp_max_ttl( traces, options.max_ttl )
    
#    mx_input_sets = dict([(act,max_input_sets) for act in var_info.alphabet])
#    for act, num_sets in explicit_max_input_sets:
#        mx_input_sets[act] = int(num_sets)
#    constraint_number += generate_stp_max_input_sets( traces,  
#                            var_info, mx_input_sets )
#                            
#    mx_output_sets = dict([(act,max_output_sets) for act in var_info.alphabet])
#    for act, num_sets in explicit_max_output_sets:
#        mx_output_sets[act] = int(num_sets)
#    constraint_number += generate_stp_max_output_sets( traces,  
#                            var_info, mx_output_sets )
#    
#    constraint_number += generate_stp_min_equal_input_sets( traces,  
#                            var_info, mx_input_sets, options.min_global_input_sets )
    ###DEBUG
    #options.binding_seq=[['a', set([]), set(['b'])], ['b', set(['a']), set(['c', 'b'])], ['c', set(['b']), set(['d'])], ['d', set(['c']), set(['d'])], ['b', set(['b']), set(['c'])], ['c', set(['b']), set(['d'])], ['d', set(['c', 'd']), set(['e'])], ['e', set(['d']), set([])]]
    ###END DEBUG
    if binding_seq:
        constraint_number += generate_stp_avoid_binding_seq( log_info, var_info,
                            binding_seq, options )

    print "%Total number of constraints:", constraint_number
    print
    print "QUERY (FALSE);"
    print "COUNTEREXAMPLE;"
    #print obligation_dict
    #return obligation_dict
    
#def main():
#    """Main function of this module, called if the module is directly called"""
#    parser = OptionParser(usage="%prog [options] filename", version="%prog 0.1",
#                description=("Prints the arithmetic constraint problem, "
#                        "in CVC format, that encode the C-net discovery "
#                        "problem for the given log."))
#    add_parser_options( parser )
#    (options, args) = parser.parse_args()
#    variables = []
#    if len(args) != 1:
#        parser.error("incorrect number of arguments. Type -h for help.")
#    try:
#        logfile = open(args[0])
#    except Exception as ex:
#        print("Error. Cannot open file '%s'. %s" % (args[0], ex))
#        quit()
#    log_info = load_log( logfile )
#    traces = log_info.traces
#    logfile.close()
#    seq_ts = build_seq_ts( traces )
#    var_info = boolean_variables( traces, options, seq_ts )
#    net = cnet.build_sequential_cnet(args[0])
#    #deviations = net.simulate_ts( seq_ts )
#    deviations = []
#    generate_stp_from_log( log_info, var_info, deviations, options, seq_ts )
#    #seq_ts.print_ts()
#    
#    if options.debug:
#        print deviations
#
#if __name__ == '__main__':
#    main()
