import re
import os
from io import open

import itertools
import numpy as np

debug_mode = False


def print_debug_output(results, dt):
        print("\n\n\nDETERMINISTIC TERMS: " + dt)
        alpha = results["est"]["alpha"]
        print("alpha:")
        print(str(type(alpha)) + str(alpha.shape))
        print(alpha)
        print("se: ")
        print(results["se"]["alpha"])
        print("t: ")
        print(results["t"]["alpha"])
        print("p: ")
        print(results["p"]["alpha"])
        beta = results["est"]["beta"]
        print("beta:")
        print(str(type(beta)) + str(beta.shape))
        print(beta)
        gamma = results["est"]["Gamma"]
        print("Gamma:")
        print(str(type(gamma)) + str(gamma.shape))
        print(gamma)
        if "co" in dt or "s" in dt or "lo" in dt:
            c = results["est"]["C"]
            print("C:")
            print(str(type(c)) + str(c.shape))
            print(c)
            print("se: ")
            print(results["se"]["C"])


def dt_s_tup_to_string(dt_s_tup):
    dt_string = dt_s_tup[0]  # string for identifying the file to parse.
    if dt_s_tup[1] > 0:  # if there are seasons in the model
        if "co" in dt_string or "ci" in dt_string or "nc" in dt_string:
            dt_string = dt_string[:2] + "s" + dt_string[2:]
        else:
            dt_string = "s" + dt_string
    return dt_string


def sublists(lst, min_elmts=0, max_elmts=None):
    """Build a list of all possible sublists of a given list. Restrictions
    on the length of the sublists can be posed via the min_elmts and max_elmts
    parameters.
    All sublists
    have will have at least min_elmts elements and not more than max_elmts
    elements.

    Parameters
    ----------
    lst : list
        Original list from which sublists are generated.
    min_elmts : int
        Lower bound for the length of sublists.
    max_elmts : int or None
        If int, then max_elmts are the upper bound for the length of sublists.
        If None, sublists' length is not restricted. In this case the longest
        sublist will be of the same length as the original list lst.

    Returns
    -------
    result : list
        A list of all sublists of lst fulfilling the length restrictions.
    """
    if max_elmts is None:
        max_elmts = len(lst)
    # for the following see also the definition of powerset() in
    # https://docs.python.org/dev/library/itertools.html#itertools-recipes
    result = itertools.chain.from_iterable(
                itertools.combinations(lst, sublist_len)
                for sublist_len in range(min_elmts, max_elmts+1))
    if type(result) != list:
        result = list(result)
    return result


def stringify_var_names(var_list):
    """

    Parameters
    ----------
    var_list : list of strings
        Each list element is the name of a variable.

    Returns
    -------
    result : string
        Concatenated variable names.
    """
    result = ""
    for var_name in var_list:
        result += var_name
    return result.lower()


def load_results_jmulti(dataset, dt_s_list):
    """

    Parameters
    ----------
    dataset : module
        A data module in the statsmodels/datasets directory that defines a
        __str__() method returning the dataset's name.
    dt_s_list : list
        A list of strings where each string represents a combination of
        deterministic terms.

    Returns
    -------
    result : dict
        A dict (keys: tuples of deterministic terms and seasonal terms)
        of dicts (keys: strings "est" (for estimators),
                              "se" (for standard errors),
                              "t" (for t-values),
                              "p" (for p-values))
        of dicts (keys: strings "alpha", "beta", "Gamma" and other results)
    """
    source = "jmulti"

    results_dict_per_det_terms = dict.fromkeys(dt_s_list)
        
    for dt_s in dt_s_list:
        dt_string = dt_s_tup_to_string(dt_s)
        params_file = dataset.__str__()+"_"+source+"_"+dt_string+".txt"
        params_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   params_file)
        # sections in jmulti output:
        section_header = ["Lagged endogenous term",  # Gamma
                          "Deterministic term",      # co, s, lo
                          "Loading coefficients",    # alpha
                          "Estimated cointegration relation",  # beta
                          "Legend",
                          "Lagged endogenous term",  # VAR representation
                          "Deterministic term"]      # VAR representation
        # the following "sections" will serve as key for the corresponding
        # result values
        sections = ["Gamma",
                    "C",     # Here all deterministic term coefficients are
                             # collected. (const and linear trend which belong
                             # to cointegration relation as well as seasonal
                             # components which are outside the cointegration
                             # relation. Later, we will strip the terms related
                             # to the cointegration relation from C.
                    "alpha",
                    "beta",
                    "Legend",
                    "VAR A",  # VAR parameter matrices
                    "VAR deterministic"]  # VAR deterministic terms
        if "co" not in dt_string and "lo" not in dt_string \
                and "s" not in dt_string:
            # JMulTi: no deterministic terms section in VEC representation
            del(section_header[1])
            del(sections[1])
            if "ci" not in dt_string and "li" not in dt_string:
                # JMulTi: no deterministic section in VAR repr.
                del(section_header[-1])
                del(sections[-1])
        results = dict()
        results["est"] = dict.fromkeys(sections)
        results["se"] = dict.fromkeys(sections)
        results["t"] = dict.fromkeys(sections)
        results["p"] = dict.fromkeys(sections)
        section = -1
        result = []
        result_se = []
        result_t = []
        result_p = []

        rows = 0
        started_reading_section = False
        start_end_mark = "-----"

        # ---------------------------------------------------------------------
        # parse information about \alpha, \beta, \Gamma, deterministic of VECM
        # and A_i and deterministic of corresponding VAR:
        params_file = open(params_file)
        for line in params_file:
            if section == -1 and section_header[section+1] not in line:
                continue
            if section < len(section_header)-1 \
                    and section_header[section+1] in line:  # new section
                section += 1
                continue
            if not started_reading_section:
                if line.startswith(start_end_mark):
                    started_reading_section = True
                continue
            if started_reading_section:
                if line.startswith(start_end_mark):
                    if result == []:  # no values collected in section "Legend"
                        started_reading_section = False
                        continue
                    results["est"][sections[section]] = np.column_stack(
                                                                    result)
                    result = []
                    results["se"][sections[section]] = np.column_stack(
                                                                    result_se)
                    result_se = []
                    results["t"][sections[section]] = np.column_stack(
                                                                    result_t)
                    result_t = []
                    results["p"][sections[section]] = np.column_stack(
                                                                    result_p)
                    result_p = []
                    started_reading_section = False
                    continue
                str_number = "-?\d+\.\d{3}"
                regex_est = re.compile(str_number + "[^\)\]\}]")
                est_col = re.findall(regex_est, line)
                # standard errors in parantheses in JMulTi output:
                regex_se = re.compile("\(" + str_number + "\)")
                se_col = re.findall(regex_se, line)
                # t-values in brackets in JMulTi output:
                regex_t_value = re.compile("\[" + str_number + "\]")
                t_col = re.findall(regex_t_value, line)
                # p-values in braces in JMulTi output:
                regex_p_value = re.compile("\{" + str_number + "\}")
                p_col = re.findall(regex_p_value, line)
                if result == [] and est_col != []:
                    rows = len(est_col)
                if est_col != []:
                    est_col = [float(el) for el in est_col]
                    result.append(est_col)
                elif se_col != []:
                    for i in range(rows):
                        se_col[i] = se_col[i].replace("(", "").replace(")", "")
                    se_col = [float(el) for el in se_col]
                    result_se.append(se_col)
                elif t_col != []:
                    for i in range(rows):
                        t_col[i] = t_col[i].replace("[", "").replace("]", "")
                    t_col = [float(el) for el in t_col]
                    result_t.append(t_col)
                elif p_col != []:
                    for i in range(rows):
                        p_col[i] = p_col[i].replace("{", "").replace("}", "")
                    p_col = [float(el) for el in p_col]
                    result_p.append(p_col)
        params_file.close()
        # delete "Legend"-section of JMulTi:
        del results["est"]["Legend"]
        del results["se"]["Legend"]
        del results["t"]["Legend"]
        del results["p"]["Legend"]
        # JMulTi outputs beta.T
        results["est"]["beta"] = results["est"]["beta"].T
        results["se"]["beta"] = results["se"]["beta"].T
        results["t"]["beta"] = results["t"]["beta"].T
        results["p"]["beta"] = results["p"]["beta"].T
        # split information about beta and deterministic terms inside coint.
        alpha = results["est"]["alpha"]
        beta = results["est"]["beta"]
        alpha_rows = alpha.shape[0]
        if beta.shape[0] > alpha_rows:
            results["est"]["beta"], results["est"]["det_coint"] = np.vsplit(
                results["est"]["beta"], [alpha_rows])
            results["se"]["beta"], results["se"]["det_coint"] = np.vsplit(
                results["se"]["beta"], [alpha_rows])
            results["t"]["beta"], results["t"]["det_coint"] = np.vsplit(
                results["t"]["beta"], [alpha_rows])
            results["p"]["beta"], results["p"]["det_coint"] = np.vsplit(
                results["p"]["beta"], [alpha_rows])

        # ---------------------------------------------------------------------
        # parse information regarding \Sigma_u
        sigmau_file = dataset.__str__() + "_" + source + "_" + dt_string \
            + "_Sigmau" + ".txt"
        sigmau_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   sigmau_file)
        rows_to_parse = 0
        # all numbers of Sigma_u in notation with e (e.g. 2.283862e-05)
        regex_est = re.compile("\s+\S+e\S+")
        sigmau_section_reached = False
        sigmau_file = open(sigmau_file)
        for line in sigmau_file:
            if line.startswith("Log Likelihood:"):
                line = line.split("Log Likelihood:")[1]
                results["log_like"] = float(re.findall(regex_est, line)[0])
            if not sigmau_section_reached and "Covariance:" not in line:
                continue
            if "Covariance:" in line:
                sigmau_section_reached = True
                row = re.findall(regex_est, line)
                rows_to_parse = len(row)  # Sigma_u quadratic ==> #rows==#cols
                sigma_u = np.empty((rows_to_parse, rows_to_parse))
            row = re.findall(regex_est, line)
            rows_to_parse -= 1
            sigma_u[rows_to_parse] = row  # rows are added in reverse order
            if rows_to_parse == 0:
                break
        sigmau_file.close()
        results["est"]["Sigma_u"] = sigma_u[::-1]

        # ---------------------------------------------------------------------
        # parse forecast related output:
        fc_file = dataset.__str__() + "_" + source + "_" + dt_string \
            + "_fc5" + ".txt"
        fc_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               fc_file)
        fc, lower, upper, plu_min = [], [], [], []
        fc_file = open(fc_file, encoding='latin_1')
        for line in fc_file:
            str_number = "(\s+-?\d+\.\d{3}\s*)"
            regex_number = re.compile(str_number)
            numbers = re.findall(regex_number, line)
            if numbers == []:
                continue
            fc.append(float(numbers[0]))
            lower.append(float(numbers[1]))
            upper.append(float(numbers[2]))
            plu_min.append(float(numbers[3]))
        fc_file.close()
        variables = alpha.shape[0]
        fc = np.hstack(np.vsplit(np.array(fc)[:, None], variables))
        lower = np.hstack(np.vsplit(np.array(lower)[:, None], variables))
        upper = np.hstack(np.vsplit(np.array(upper)[:, None], variables))
        # plu_min = np.hstack(np.vsplit(np.array(plu_min)[:, None], variables))
        results["fc"] = dict.fromkeys(["fc", "lower", "upper"])
        results["fc"]["fc"] = fc
        results["fc"]["lower"] = lower
        results["fc"]["upper"] = upper

        # ---------------------------------------------------------------------
        # parse output related to Granger-causality and instant causality:
        results["granger_caus"] = dict.fromkeys(["p", "test_stat"])
        results["inst_caus"] = dict.fromkeys(["p", "test_stat"])
        results["granger_caus"]["p"] = dict()
        results["granger_caus"]["test_stat"] = dict()
        results["inst_caus"]["p"] = dict()
        results["inst_caus"]["test_stat"] = dict()
        vn = dataset.variable_names
        # all possible combinations of potentially causing variables
        # (at least 1 variable and not all variables together):
        var_combs = sublists(vn, 1, len(vn)-1)
        for causing in var_combs:
            # Now that the potentially causing variables are fixed, find all
            # combinations of potentially caused variables.
            causing_compl = [el for el in vn if el not in causing]
            caused_combs = sublists(causing_compl, 1, len(causing_compl))
            for caused in caused_combs:
                granger_file = dataset.__str__() + "_" + source + "_" \
                    + dt_string + "_granger_causality_" \
                    + stringify_var_names(causing) + "_" \
                    + stringify_var_names(caused) + ".txt"
                granger_file = os.path.join(os.path.dirname(
                        os.path.realpath(__file__)), granger_file)
                granger_file = open(granger_file)
                granger_results = []
                for line in granger_file:
                    str_number = "\d+\.\d{4}"
                    regex_number = re.compile(str_number)
                    number = re.search(regex_number, line)
                    if number is None:
                        continue
                    number = float(number.group(0))
                    granger_results.append(number)
                granger_file.close()
                results["granger_caus"]["test_stat"][(causing, caused)] = \
                    granger_results[0]

                results["granger_caus"]["p"][(causing, caused)] =\
                    granger_results[1]
                results["inst_caus"]["test_stat"][(causing, caused)] = \
                    granger_results[2]
                results["inst_caus"]["p"][(causing, caused)] = \
                    granger_results[3]

        # ---------------------------------------------------------------------
        # parse output related to impulse-response analysis:
        ir_file = dataset.__str__() + "_" + source + "_" + dt_string \
            + "_ir" + ".txt"
        ir_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               ir_file)
        ir_file = open(ir_file, encoding='latin_1')
        causing = None
        caused = None
        data = None
        regex_vars = re.compile("\w+")
        regex_vals = re.compile("-?\d+\.\d{4}")
        line_start_causing = "time"
        data_line_indicator = "point estimate"
        data_rows_read = 0
        for line in ir_file:
            if causing is None and not line.startswith(line_start_causing):
                continue  # no relevant info in the header
            if line.startswith(line_start_causing):
                line = line[4:]
                causing = re.findall(regex_vars, line)
                # 21 periods shown in JMulTi output
                data = np.empty((21, len(causing)))
                continue
            if caused is None:
                caused = re.findall(regex_vars, line)
                continue
            # now start collecting the values:
            if data_line_indicator not in line:
                continue
            start = line.find(data_line_indicator) + len(data_line_indicator)
            line = line[start:]
            data[data_rows_read] = re.findall(regex_vals, line)
            data_rows_read += 1
        ir_file.close()
        results["ir"] = data

        # ---------------------------------------------------------------------
        if debug_mode:
            print_debug_output(results, dt_string)

        results_dict_per_det_terms[dt_s] = results

    return results_dict_per_det_terms
