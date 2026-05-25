from random import random, randrange, uniform, choices

# from drs import drs
from convolutionalfixedsum import cfsn
from scipy.stats import loguniform

from Task import Task
from TaskSet import TaskSet

U_MIN = 0
U_MAX = 1

P_pool = [10, 20, 50, 100]  # Weighted pool of periods for tasks
P_weights = [25, 25, 3, 20]  # Weights for the periods in the pool

def generate_task_uniform(probability_of_HI, wcet_HI_ratio, max_wcet_LO, min_period, max_period):
    offset = 0

    # period = round(loguniform.rvs(min_period, max_period))
    period = choices(P_pool, weights=P_weights, k=1)[0]

    wcet = [randrange(1, min(max_wcet_LO, period) + 1)] * 2

    if random() <= probability_of_HI:
        criticality_level = 1
        wcet[1] = randrange(wcet[0], min(int(round(wcet_HI_ratio * wcet[0])), period) + 1)
    else:
        criticality_level = 0

    deadline = period  # implicit deadline

    return Task(offset, period, deadline, criticality_level, wcet)


def generate_random_task_set(n_tasks, probability_of_HI, wcet_HI_ratio, max_wcet_LO, max_period, min_period):
    ts = TaskSet()

    done = False
    while not done:
        ts.clear()
        while len(ts) < n_tasks:
            ts.add_task(
                generate_task_uniform(
                    probability_of_HI=probability_of_HI,
                    wcet_HI_ratio=wcet_HI_ratio,
                    max_wcet_LO=max_wcet_LO,
                    min_period=min_period,
                    max_period=max_period,
                )
            )
            if ts.get_utilisation_of_level(0) > 1 or ts.get_utilisation_of_level(1) > 1:
                break
        else:
            if not ((ts.tasks["X"] == ts.tasks.loc[0, "X"]).all()):
                done = True
    return ts


def generate_task_set_with_utilisation(
    n_tasks: int, target_average_utilisation: float, target_switching_factor: float, min_period: int, max_period: int, probability_of_HI: float, tolerance=0.005, verbose=False
):
    assert n_tasks > 1, "n_tasks must be at least 2"
    assert target_average_utilisation >= U_MIN, f"u_target must be greater than {U_MIN}"
    assert target_average_utilisation <= U_MAX, f"u_target must be less than {U_MAX}"
    assert target_switching_factor >= 0, "target_switching_factor must be non-negative"
    assert target_switching_factor <= 1, "target_switching_factor must be less than or equal to 1"

    while True:
        # select HI tasks
        tasks_HI = [i for i in range(n_tasks) if random() <= probability_of_HI]
        if len(tasks_HI) == 0:
            if verbose:
                print("no HI tasks")
            continue
        if len(tasks_HI) == n_tasks:
            if verbose:
                print("all HI tasks")
            continue

        # draw number of HI
        n_HI = len(tasks_HI)
        # infer number of LO
        n_LO = n_tasks - n_HI

        # draw periods before hand
        periods = [loguniform.rvs(min_period, max_period) for _ in range(n_tasks)]
        periods = list(map(round, periods))
        # # draw periods from weighted pool instead
        # periods = choices(P_pool, weights=P_weights, k=n_tasks)

        # compute possible range for utilisation in LO and HI based on target average utilisation
        range_to_u_max = U_MAX - target_average_utilisation
        range_to_u_min = target_average_utilisation
        random_range = min(range_to_u_max, range_to_u_min)

        # draw utilisation of HI from possible range
        u_HI_upper_bound = min(U_MAX, target_average_utilisation + random_range)
        u_HI_lower_bound = max(U_MIN, target_average_utilisation - random_range)
        u_HI = uniform(u_HI_lower_bound, u_HI_upper_bound)

        # infer utilisation of LO to match target average utilisation
        u_LO = 2 * target_average_utilisation - u_HI

        # tasks must have a min wcst of 1, this inferieng what is the min utilisation based on the period
        u_min_for_S = [1 / periods[i] for i in tasks_HI]
        if target_switching_factor > 0:
            u_HI_LO_min = sum(u_min_for_S) / target_switching_factor
        else:
            u_HI_LO_min = 0

        if u_HI_LO_min >= min(u_HI, u_LO):
            if verbose:
                print(f"u_HI_LO_min >= min(u_HI, u_LO): {u_HI_LO_min} >= {min(u_HI, u_LO)}")
            continue

        # draw utilisation of U_HI_LO uniformly from possible range
        u_HI_LO = uniform(u_HI_LO_min, min(u_HI, u_LO))
        u_S = target_switching_factor * u_HI_LO

        u_avg = (u_HI + u_LO) / 2  # should always be == u_target
        if u_avg != target_average_utilisation:
            if verbose:
                print(f"u_avg != u_target: {u_avg} != {target_average_utilisation}")
            continue

        if n_HI == 1:
            u_S_tasks_HI = [u_S]
        elif target_switching_factor > 0:
            try:
                u_S_tasks_HI = cfsn(n_HI, u_S, lower_constraints=u_min_for_S)
            except ZeroDivisionError:
                if verbose:
                    print("ZeroDivisionError in CFSN utilisation in S")
                continue 
            except Exception as e:
                print(f"Exception in CFSN utilisation in S: {e}")
                print(f"n_tasks={n_tasks}, u_S={u_S}, u_min_for_S={u_min_for_S}")
                exit(1)
        else:
            u_S_tasks_HI = [0] * n_HI

        # reconstruct full list to resume normal execution
        u_S_tasks = [0] * n_tasks
        u_min_in_LO = [1 / p for p in periods]
        for task_idx, u_s_task in zip(tasks_HI, u_S_tasks_HI):
            u_S_tasks[task_idx] = u_s_task
            u_min_in_LO[task_idx] = u_s_task

        # for CFSN, lower bounds must sum to less than max utilisation
        if sum(u_min_in_LO) > u_LO:
            if verbose:
                print(f"sum(u_min_in_LO) > u_LO: {sum(u_min_in_LO)} > {u_LO}")
            continue

        # using CFSN to draw task level utilisation in LO
        try:
            u_LO_tasks = cfsn(n_tasks, u_LO, lower_constraints=u_min_in_LO)
        except ZeroDivisionError:
            if verbose:
                print("ZeroDivisionError in CFSN utilisation in LO")
            continue

        # defining lower and upper bounds only for HI tasks in HI
        # another workaround for a bug in CFSN that it would fail when lower bound is equal to the upper bound.
        # generate only the HI entries, then place them back in task order after generation.
        u_min_in_HI = [u_LO_tasks[i] for i in tasks_HI]
        u_max_in_HI = [U_MAX] * n_HI

        # for CFSN, lower bounds must sum to less than max utilisation
        if sum(u_min_in_HI) > u_HI:
            if verbose:
                print(f"sum(u_min_in_HI) > u_HI: {sum(u_min_in_HI)} > {u_HI}")
            continue

        # using CFSN to draw task level utilisation of HI tasks in HI
        # this is just a workaround for a bug in CFSN when N=1 for HI criticality tasks where it will fail.
        if n_HI == 1:
            u_HI_tasks_HI = [u_HI]
        else:
            try:
                u_HI_tasks_HI = cfsn(n_HI, total=u_HI, upper_constraints=u_max_in_HI, lower_constraints=u_min_in_HI)
            except ZeroDivisionError:
                if verbose:
                    print("ZeroDivisionError in CFSN utilisation in HI")
                continue
            except Exception as e:
                print(f"Exception in CFSN utilisation in HI: {e}")
                print(f"n_tasks={n_tasks}, u_HI={u_HI}, u_max_in_HI={u_max_in_HI}, u_min_in_HI={u_min_in_HI}")
                exit(1)

        # reconstruct full list to resume normal execution
        u_HI_tasks = [0] * n_tasks
        for task_idx, u_hi_task in zip(tasks_HI, u_HI_tasks_HI):
            u_HI_tasks[task_idx] = u_hi_task

        task_set = TaskSet()

        for i, period, u_S, u_LO, u_HI in zip(range(n_tasks), periods, u_S_tasks, u_LO_tasks, u_HI_tasks):
            wcst = max(1, round(period * u_S))
            wcet_LO = max(1, round(period * u_LO))
            wcet = [wcet_LO] * 2
            criticality_level = 0
            if i in tasks_HI:
                wcet[1] = round(period * u_HI)
                criticality_level = 1

            offset = 0
            deadline = period  # implicit deadline
            task = Task(offset, period, deadline, criticality_level, wcet, wcst)

            task_set.add_task(task)

        u_LO_generated = task_set.get_utilisation_of_level(0)
        u_HI_generated = task_set.get_utilisation_of_level(1)
        generated_average_utilisation = (u_LO_generated + u_HI_generated) / 2

        delta_u_avg = generated_average_utilisation - target_average_utilisation

        # Utilisation cannot be above 1
        if u_LO_generated > 1:
            if verbose:
                print(f"u_LO_generated>1: {u_LO_generated}")
            continue
        if u_HI_generated > 1:
            if verbose:
                print(f"u_HI_generated>1: {u_HI_generated}")
            continue
        # Tolerance check
        if abs(delta_u_avg) > tolerance:
            if verbose:
                print(f"abs(delta_u_avg) > tolerance: {abs(delta_u_avg)} > {tolerance}")
            continue

        recap_str = f"""
        Generating a set of {n_tasks} with target actual utilisation of {target_average_utilisation} and target switching factor of {target_switching_factor}.

        Randomly drawn number of HI tasks = {n_HI}
        Hence, number of LO tasks = {n_LO}

        HI tasks have ids: {tasks_HI}

        Utilisation of Switching = {u_S}
        Utilisation of LO tasks = {u_LO}
        Utilisation of HI tasks = {u_HI}
        -> Average utilisation = {u_avg}

        Loads of tasks for switching = {u_S_tasks}
        Loads of tasks in mode LO = {u_LO_tasks}
        Loads of tasks in mode HI = {u_HI_tasks}
        """
        if verbose:
            print(recap_str)
            print(task_set)
            print(f"Utilisation in LO = {u_LO_generated:.4f}, delta to target = {u_LO_generated - u_LO:.4f}")
            print(f"Utilisation in HI = {u_HI_generated:.4f}, delta to target = {u_HI_generated - u_HI:.4f}")
            print(
                f"Average utilisation = {generated_average_utilisation:.4f}, delta to target = {generated_average_utilisation - u_avg:.4f}"
            )

        return task_set
