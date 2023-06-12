import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

# * https://github.com/BYU-PRISM/GEKKO


class MatchmakerOptimizer:
    """Use pytorch to optimize the team directly"""

    def __init__(self, skills, player_per_team) -> None:
        self.player_per_team = player_per_team
        self.skills = torch.Tensor(skills)
        self.cstr_w = 100

        n1 = torch.rand_like(self.skills)

        self.team1 = nn.Parameter(n1)
        self.team2 = nn.Parameter(1 - n1)

    def parameters(self):
        return [self.team1, self.team2]

    def normalized(self):
        clamped1 = self.team1.clamp(0, 10)
        clamped2 = self.team1.clamp(0, 10)

        norm1 = clamped1 / clamped1.sum()
        norm2 = clamped2 / clamped2.sum()

        return norm1, norm2

    def cstr_mutually_exclusive(self):
        """"""
        norm1, norm2 = self.normalized()
        return (norm1 * norm2).sum() * self.cstr_w

    def cstr_full_team(self):
        """(sum(team) - #player) * l1"""
        norm1, norm2 = self.normalized()

        player_count1 = sum(norm1) - self.player_per_team
        player_count2 = sum(norm2) - self.player_per_team

        return (player_count1**2 + player_count2**2) * self.cstr_w

    def base_cost(self):
        norm1, norm2 = self.normalized()

        skill_1 = (self.skills * norm1).sum()
        skill_2 = (self.skills * norm2).sum()
        return (skill_1 - skill_2) ** 2

    def cost(self):
        cstr1 = self.cstr_full_team()
        cstr2 = self.cstr_mutually_exclusive()

        return self.base_cost() + cstr1 + cstr2

    def optimize(self):
        optimizer = optim.SGD(self.parameters(), lr=0.001)

        for _ in range(100):
            optimizer.zero_grad()
            cost = self.cost()
            cost.backward()
            optimizer.step()

        return cost.item()

    def get_assignation(self):
        t1 = self.team1.t().topk(self.player_per_team).indices
        t2 = self.team2.t().topk(self.player_per_team).indices

        return t1, t2

    def get_team_skills(self):
        teams = self.get_assignation()
        skills = [0, 0]

        for i, t in enumerate(teams):
            for pidx in t:
                skills[i] += self.skills[pidx]

        for i, _ in enumerate(skills):
            skills[i] = skills[i] / self.player_per_team

        return skills


def main():
    import numpy as np
    import random

    pool = np.array(
        [
            1500 - 4 + random.randint(-100, 100),
            1500 - 3 + random.randint(-100, 100),
            1500 - 2 + random.randint(-100, 100),
            1500 - 1 + random.randint(-100, 100),
            1500 + 0 + random.randint(-100, 100),
            1500 + 0 + random.randint(-100, 100),
            1500 + 1 + random.randint(-100, 100),
            1500 + 2 + random.randint(-100, 100),
            1500 + 3 + random.randint(-100, 100),
            1500 + 4 + random.randint(-100, 100),
        ]
    )

    mm = MatchmakerOptimizer(pool, 2)

    mm.optimize()

    # print("t1:", mm.team1.t())
    # print("t2:", mm.team2.t())

    print(mm.get_assignation())
    print(mm.get_team_skills())
    print(mm.cstr_mutually_exclusive())


if __name__ == "__main__":
    main()
