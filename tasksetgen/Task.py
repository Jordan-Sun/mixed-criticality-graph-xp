import pandas as pd


class Task:
    def __init__(self, O: int, T: int, D: int, X: int, C: list[int], C_s = 0):
        C_indices = [f"C{i}" for i in range(len(C))]
        self.task = pd.Series([O, T, D, X, C_s] + list(C), ["O", "T", "D", "X", "C_s"] + C_indices)
        U = pd.Series(
            (self.task[C_indices] / self.task["T"]).values,
            index=["U" + str(i) for i in range(len(C))],
        )
        if X == 0:
            U["U1"] = 0

        self.task = pd.concat([self.task, U])
