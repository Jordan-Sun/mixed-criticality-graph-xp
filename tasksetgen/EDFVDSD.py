def test(task_set):
    utilisation_of_LO_at_LO = task_set.get_utilisation_of_level_at_level(0, 0)
    utilisation_of_HI_at_LO = task_set.get_utilisation_of_level_at_level(1, 0)
    utilisation_of_HI_at_HI = task_set.get_utilisation_of_level_at_level(1, 1)

    utilisation_at_LO = utilisation_of_LO_at_LO + utilisation_of_HI_at_LO
    utilisation_at_HI = utilisation_of_HI_at_HI

    if utilisation_at_LO > 1:
        return False
    if utilisation_at_HI > 1:
        return False

    if utilisation_of_LO_at_LO == 1:
        return (utilisation_of_HI_at_LO == 0) and (utilisation_of_HI_at_HI == 0)
    
    x = utilisation_of_HI_at_LO / (1 - utilisation_of_LO_at_LO)
    if x == 1:
        return False

    utilisation_EDFVDSD = 0

    # rename columns to allow itertuple to work
    task_set_df = task_set.get_df()

    for task in task_set_df.itertuples():
        if task.X == 1:
            T_i = task.T
            C_i_S = task.C_s
            C_i_LO = task.C0
            u_i_LO = task.U0
            u_i_HI = task.U1

            lhs = u_i_HI / (1 - x * C_i_S / C_i_LO)
            rhs = (u_i_LO - C_i_S / T_i) / (1 - x)
            max_term = max(lhs, rhs)
            utilisation_EDFVDSD += max_term

    return utilisation_EDFVDSD <= 1
