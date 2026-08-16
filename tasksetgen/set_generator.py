from random import random, randrange, sample, uniform

# from drs import drs
from convolutionalfixedsum import cfsn
from scipy.stats import loguniform

from Task import Task
from TaskSet import TaskSet

U_MIN = 0
U_MAX = 1
ALLOCATION_RETRY_LIMIT = 10

# P_pool = [10, 20, 50, 100]  # Weighted pool of periods for tasks
# P_weights = [25, 25, 3, 20]  # Weights for the periods in the pool


def generate_task_uniform(probability_of_HI, wcet_HI_ratio, max_wcet_LO, min_period, max_period):
    offset = 0

    period = round(loguniform.rvs(min_period, max_period))
    # period = choices(P_pool, weights=P_weights, k=1)[0]

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


def _draw_mixed_criticality_count(n_tasks, probability_of_HI):
    """Draw a conditional-binomial HI-task count with both levels present."""
    while True:
        n_HI = sum(random() <= probability_of_HI for _ in range(n_tasks))
        if 0 < n_HI < n_tasks:
            return n_HI


def generate_task_set_with_utilisation(
    n_tasks: int,
    target_average_utilisation: float,
    target_switching_factor: float,
    min_period: int,
    max_period: int,
    probability_of_HI: float,
    tolerance=0.005,
    verbose=False,
):
    assert n_tasks > 1, "n_tasks must be at least 2"
    assert target_average_utilisation >= U_MIN, f"u_target must be greater than {U_MIN}"
    assert target_average_utilisation <= U_MAX, f"u_target must be less than {U_MAX}"
    assert target_switching_factor >= 0, "target_switching_factor must be non-negative"
    assert target_switching_factor <= 1, "target_switching_factor must be less than or equal to 1"

    # Keep the criticality counts fixed for the lifetime of this generator
    # call. Otherwise, count-dependent allocation success rates bias the
    # returned distribution toward configurations that are easier to round.
    n_HI = _draw_mixed_criticality_count(n_tasks, probability_of_HI)
    n_LO = n_tasks - n_HI

    while True:
        # Task identities may change when the remaining definition is redrawn,
        # but the sampled number of tasks at each criticality cannot.
        tasks_HI = sample(range(n_tasks), k=n_HI)
        tasks_LO = [i for i in range(n_tasks) if i not in tasks_HI]

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

        # draw utilisation of U_HI_LO uniformly from possible range
        u_HI_LO = uniform(0, min(u_HI, u_LO))
        u_S = target_switching_factor * u_HI_LO

        u_avg = (u_HI + u_LO) / 2  # should always be == u_target
        if u_avg != target_average_utilisation:
            if verbose:
                print(f"u_avg != u_target: {u_avg} != {target_average_utilisation}")
            continue

        periods_LO = [periods[i] for i in tasks_LO]
        u_LO_LO = u_LO - u_HI_LO
        u_min_tasks_LO = [1 / period for period in periods_LO]

        if sum(u_min_tasks_LO) > u_LO_LO:
            if verbose:
                print("U_LO_LO not high enough for unit execution time for each LO task")
            continue

        periods_HI = [periods[i] for i in tasks_HI]
        u_min_tasks_HI = [1 / period for period in periods_HI]

        if sum(u_min_tasks_HI) > u_HI_LO:
            if verbose:
                print("U_HI_LO not high enough for unit execution time for each HI task")
            continue

        u_max_in_HI = [U_MAX] * n_HI
        if u_HI_LO > u_HI or u_HI > sum(u_max_in_HI):
            if verbose:
                print(f"HI-mode constraints do not contain target utilisation: {u_HI}")
            continue

        # Keep the sampled task-set definition fixed while retrying only the
        # stochastic per-task allocations and their rounded WCETs.
        for allocation_attempt in range(ALLOCATION_RETRY_LIMIT):
            try:
                if n_LO == 1:
                    u_LO_tasks_LO = [u_LO_LO]
                elif sum(u_min_tasks_LO) == u_LO_LO:
                    u_LO_tasks_LO = u_min_tasks_LO
                else:
                    u_LO_tasks_LO = cfsn(n_LO, u_LO_LO, lower_constraints=u_min_tasks_LO)

                if n_HI == 1:
                    u_LO_tasks_HI = [u_HI_LO]
                elif sum(u_min_tasks_HI) == u_HI_LO:
                    u_LO_tasks_HI = u_min_tasks_HI
                else:
                    u_LO_tasks_HI = cfsn(n_HI, u_HI_LO, lower_constraints=u_min_tasks_HI)

                if target_switching_factor == 0:
                    u_S_tasks_HI = [0] * n_HI
                elif target_switching_factor == 1:
                    u_S_tasks_HI = u_LO_tasks_HI
                elif n_HI == 1:
                    u_S_tasks_HI = [u_S]
                else:
                    u_S_tasks_HI = cfsn(n_HI, u_S, upper_constraints=u_LO_tasks_HI)

                if n_HI == 1:
                    u_HI_tasks_HI = [u_HI]
                elif sum(u_LO_tasks_HI) == u_HI:
                    u_HI_tasks_HI = u_LO_tasks_HI
                elif sum(u_max_in_HI) == u_HI:
                    u_HI_tasks_HI = u_max_in_HI
                else:
                    u_HI_tasks_HI = cfsn(
                        n_HI, total=u_HI, upper_constraints=u_max_in_HI, lower_constraints=u_LO_tasks_HI
                    )
            except ZeroDivisionError:
                if verbose:
                    print(f"ZeroDivisionError in CFSN allocation attempt {allocation_attempt + 1}")
                continue

            task_set = TaskSet()
            rounded_constraints_valid = True

            for period, u_LO_task in zip(periods_LO, u_LO_tasks_LO):
                wcet_LO = round(period * u_LO_task)
                if not (0 <= wcet_LO <= period):
                    rounded_constraints_valid = False
                    break
                task_set.add_task(Task(0, period, period, 0, [wcet_LO] * 2, 0))

            if not rounded_constraints_valid:
                continue

            for period, u_S_task, u_LO_task, u_HI_task in zip(periods_HI, u_S_tasks_HI, u_LO_tasks_HI, u_HI_tasks_HI):
                wcst = round(period * u_S_task)
                wcet_LO = round(period * u_LO_task)
                wcet_HI = round(period * u_HI_task)
                if not (wcst <= wcet_LO <= wcet_HI <= period):
                    rounded_constraints_valid = False
                    break
                task_set.add_task(Task(0, period, period, 1, [wcet_LO, wcet_HI], wcst))

            if not rounded_constraints_valid:
                continue

            u_LO_generated = task_set.get_utilisation_of_level(0)
            u_HI_generated = task_set.get_utilisation_of_level(1)
            generated_average_utilisation = (u_LO_generated + u_HI_generated) / 2
            delta_u_avg = generated_average_utilisation - target_average_utilisation

            if u_LO_generated > U_MAX or u_HI_generated > U_MAX or abs(delta_u_avg) > tolerance:
                if verbose:
                    print(
                        f"allocation attempt {allocation_attempt + 1} failed: "
                        f"U_LO={u_LO_generated}, U_HI={u_HI_generated}, delta={delta_u_avg}"
                    )
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

            Loads of LO tasks in mode LO = {u_LO_tasks_LO}
            Loads of HI tasks for switching = {u_S_tasks_HI}
            Loads of HI tasks in mode LO = {u_LO_tasks_HI}
            Loads of HI tasks in mode HI = {u_HI_tasks_HI}
            """
            if verbose:
                print(recap_str)
                print(task_set)
                print(f"Utilisation in LO = {u_LO_generated:.4f}, delta to target = {u_LO_generated - u_LO:.4f}")
                print(f"Utilisation in HI = {u_HI_generated:.4f}, delta to target = {u_HI_generated - u_HI:.4f}")
                print(
                    f"Average utilisation = {generated_average_utilisation:.4f}, "
                    f"delta to target = {generated_average_utilisation - u_avg:.4f}"
                )

            return task_set

        if verbose:
            print(
                f"all {ALLOCATION_RETRY_LIMIT} allocation attempts failed; "
                f"resampling task-set definition with n_HI={n_HI} and n_LO={n_LO} fixed"
            )
