import torch
import torch.nn as nn
import torch.optim as optim


class MatchmakerModel(nn.Module):
    """ML `Classifier` that tries to learn how to group teams"""

    def __init__(self, pool_size, skill_shift, player_per_team, n_teams) -> None:
        super().__init__()

        self.skill_shift = skill_shift
        self.pool_size = pool_size
        self.n_teams = n_teams
        self.player_per_team = player_per_team
        self.model = nn.Sequential(
            nn.Linear(pool_size, pool_size * pool_size),
            nn.ReLU(),
            nn.Linear(pool_size * pool_size, pool_size * n_teams),
            nn.ReLU(),
            nn.Linear(pool_size * n_teams, pool_size * n_teams),
        )

    def forward(self, batch):
        x = batch - self.skill_shift  # (n x n_players)
        x = self.model(x)  # (n x n_players * n_teams)

        x = x.view(-1, self.pool_size, self.n_teams)  # (n x n_players x n_teams)
        passignation = nn.functional.softmax(x, dim=1)

        batch_3d = batch.view(-1, 1, self.pool_size)
        skills = torch.bmm(batch_3d, passignation).view(-1, self.n_teams)
        cost = (skills[:, 0] - skills[:, 1]) ** 2

        # Ask the assignation to be mutually exclusive
        team1 = passignation[:, :, 0]
        team2 = passignation[:, :, 1]
        exclusive = torch.mul(team1, team2).sum(dim=1)

        # Ask the assignation to respect the number of players
        player1 = team1.sum(dim=1)
        player2 = team1.sum(dim=1)
        count = torch.ones_like(player1) * self.player_per_team
        count = (torch.square(player1 - count) + torch.square(player2 - count)).sum()

        return passignation, (cost + count * 1000 + exclusive * 100).sum()

    def get_assingment(self, passignation):
        """Returns the indices of the selected players"""
        result = passignation.topk(2, dim=1)

        # (n x players x teams)
        return result.indices

    def get_team_skills(self, batch, passignation):
        ass = self.get_assingment(passignation)
        bsize, nplayers, nteams = ass.shape
        results = torch.zeros((bsize, nteams))

        for b in range(bsize):
            for t in range(nteams):
                for p in range(nplayers):
                    pidx = ass[b, p, t]
                    pskill = batch[b, pidx]

                    results[b, t] += pskill

        return results / nplayers


def main_model():
    import numpy as np

    pool = np.array(
        [
            1500 - 4,
            1500 - 3,
            1500 - 2,
            1500 - 1,
            1500 + 0,
            1500 + 0,
            1500 + 1,
            1500 + 2,
            1500 + 3,
            1500 + 4,
        ]
    )

    batch = torch.stack(
        [  # (3 x 10)  batch of size 3
            torch.Tensor(pool),
            torch.Tensor(pool),
            torch.Tensor(pool),
        ]
    )

    model = MatchmakerModel(10, 1500, 2, 2)
    optimizer = optim.SGD(model.parameters(), lr=0.01)

    for _ in range(10000):
        optimizer.zero_grad()
        assignation, cost = model(batch)
        cost.backward()
        optimizer.step()

    assignation, cost = model(batch)
    result = assignation.topk(2, dim=1)

    print(result.indices, result.indices.shape)
    print(model.get_team_skills(batch, assignation))


if __name__ == "__main__":
    main_model()
