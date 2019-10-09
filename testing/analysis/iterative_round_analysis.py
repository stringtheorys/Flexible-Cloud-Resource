"""Analysis of results generated by the iterative round testing script"""

from __future__ import annotations

import json
from typing import List

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from core.core import decode_filename, save_plot, analysis_filename


matplotlib.rcParams['font.family'] = "monospace"


def plot_price_rounds(encoded_filenames: List[str], x_axis: str, title: str, save: bool = False):
    """
    Plots the price round graphs
    :param encoded_filenames: The list of encoded filenames
    :param x_axis: The x axis on the plot
    :param title: The title of the plot
    :param save: If to save the plot
    """
    data = []
    test_name: str = ""

    for encoded_filename in encoded_filenames:
        filename, model_name, test_name = decode_filename('iterative_round', encoded_filename)
        with open(filename) as file:
            file_data = json.load(file)
            for pos, model_result in enumerate(file_data):
                for name, result in model_result.items():
                    data.append([pos, model_name, name, result['initial_cost'], result['price change'],
                                 result['total_iterations'], result['total_messages'], result['total money']])

    df = pd.DataFrame(data, columns=["Pos", "Model Name", "Algorithm Name", "Initial cost", "Price Change",
                                     "Total Iterations", "Total Messages", "Total Money"])
    g = sns.FacetGrid(df, col='Model Name', sharex=False, margin_titles=True, height=4)
    # noinspection PyUnresolvedReferences
    (g.map(sns.barplot, x=x_axis, y="Algorithm Name", data=df).set_titles("{col_name}"))

    g.fig.suptitle(title)

    if save:
        save_plot(analysis_filename(test_name, x_axis), "iterative_round")
    plt.show()


if __name__ == "__main__":

    september_20 = [
        "iterative_round_results_basic_j12_s2_0",
        "iterative_round_results_basic_j15_s2_0",
        "iterative_round_results_basic_j15_s3_0",
        "iterative_round_results_basic_j25_s5_0"
    ]

    for attribute in ["Total Iterations", "Total Messages", "Total Money"]:
        plot_price_rounds(september_20, attribute, '{} of basic model'.format(attribute), save=True)
