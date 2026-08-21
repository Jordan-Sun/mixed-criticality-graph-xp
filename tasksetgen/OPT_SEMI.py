"""
The optimal semi-clairvoyant algorithm given by
[1] K. Agrawal, S. Baruah, and A. Burns, “Semi-Clairvoyance in Mixed-Criticality Scheduling,” in 2019 IEEE Real-Time Systems Symposium (RTSS), Hong Kong, Hong Kong: IEEE, Dec. 2019, pp. 458–468. doi: 10.1109/RTSS46320.2019.00047.
"""
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

    return True