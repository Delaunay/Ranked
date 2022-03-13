

def main():
    import json

    import altair as alt
    import pandas as pd

    with open("C:/opt/dota2_ranks.txt") as ranks_fs:
        data = json.load(ranks_fs)


    def showkeys(d):
        print(list(d.keys()))


    table = "mmr"
    table = "ranks"

    rows = data[table]["rows"]

    chart = (
        alt.Chart(alt.Data(values=rows))
        .mark_bar()
        .encode(
            x="bin:Q",
            y="count:Q",
        )
    )

    chart.save(f"chart_{table}.html")

    alt.renderers.enable("altair_saver", fmts=["vega-lite", "png"])
    chart.save(f"chart_{table}.png")
