"""Model Analysis"""

from __future__ import annotations

from typing import List

from core import Server
from core import Job
from core import load_dist, ModelDist

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def plot_job_distribution(model_dists: List[ModelDist], repeats: int = 10000):
    """
    Plots the job distribution of a list of models
    :param model_dists: A list of model distributions
    :param repeats: The number of repeats
    """

    """
    data = [[model_dist.name.split(",")[0], job.required_storage, job.required_computation, job.required_results_data,
             job.value, job.deadline]
            for model_dist in model_dists for _ in range(repeats) for job in model_dist.create()[0]]

    df = pd.DataFrame(data, columns=['Model', 'Storage', 'Computation', 'Results Data', 'Utility', 'Deadline'])
    wide_df = pd.melt(df, id_vars=['Model']).sort_values(['variable', 'value'])
    wide_df.rename(columns={'variable': 'Resource', 'value': 'Value'}, inplace=True)

    sns.catplot('Resource', 'Value', hue='Model', data=wide_df, kind='violin')
    plt.title("Job Distribution")
    plt.show()
    """

    data = []
    for model_dist in model_dists:
        for _ in range(repeats):
            jobs = model_dist.create()[0]
            for job in jobs:
                data.append((model_dist.dist_name, "Storage", job.required_storage))
                data.append((model_dist.dist_name, "Computation", job.required_computation))
                data.append((model_dist.dist_name, "Bandwidth", job.required_results_data))
                data.append((model_dist.dist_name, "Value", job.value))
                data.append((model_dist.dist_name, "Deadline", job.deadline))

    df = pd.DataFrame(data, columns=['Model', 'Resource', 'Value'])

    g = sns.FacetGrid(df, col='Resource', sharey=False, col_wrap=3)
    # noinspection PyUnresolvedReferences
    (g.map(sns.violinplot, 'Model', 'Value').set_titles('{col_name}'))
    plt.show()


def plot_server_distribution(model_dists: List[ModelDist], repeats: int = 10):
    """
    Plots the server distribution of a list of models
    :param model_dists: A list of model distributions
    :param repeats: The number of repeats
    """

    data = [[model_dist.dist_name, server.storage_capacity, server.computation_capacity, server.bandwidth_capacity]
            for model_dist in model_dists for _ in range(repeats) for server in model_dist.create()[1]]

    df = pd.DataFrame(data, columns=['Model', 'Storage', 'Computation', 'Results Data'])
    df = pd.melt(df, id_vars=['Model']).sort_values(['variable', 'value'])
    df.rename(columns={'variable': 'Resource', 'value': 'Value'}, inplace=True)

    sns.violinplot('Resource', 'Value', hue='Model', data=df)
    plt.title("Server Distribution")
    plt.show()


def plot_jobs(jobs: List[Job], plot_utility_deadline: bool = True):
    """
    Plots the jobs on a graph
    :param jobs: A list of jobs to plot
    :param plot_utility_deadline: Plots the utility and deadline
    """
    if plot_utility_deadline:
        data = [[job.name, job.required_storage, job.required_computation, job.required_results_data,
                 job.value, job.deadline] for job in jobs]
        df = pd.DataFrame(data, columns=['Name', 'Storage', 'Computation', 'Results Data', 'Utility', 'Deadline'])
    else:
        data = [[job.name, job.required_storage, job.required_computation, job.required_results_data] for job in jobs]
        df = pd.DataFrame(data, columns=['Name', 'Storage', 'Computation', 'Results Data'])

    wide_df = pd.melt(df, id_vars=['Name']).sort_values(['variable', 'value'])
    wide_df.rename(columns={'variable': 'Resource'}, inplace=True)
    sns.barplot(x='value', y='Name', hue='Resource', data=wide_df)
    plt.ylabel('Name')
    plt.title("Jobs")
    plt.show()


def plot_servers(servers: List[Server]):
    """
    Plots the severs on a graph
    :param servers: A list of servers to plot
    """
    data = [[server.name, server.storage_capacity, server.computation_capacity, server.bandwidth_capacity]
            for server in servers]
    df = pd.DataFrame(data, columns=['Name', 'Storage', 'Computation', 'Bandwidth'])
    wide_df = pd.melt(df, id_vars=['Name']).sort_values(['variable', 'value'])
    wide_df.rename(columns={'variable': 'Resource'}, inplace=True)
    sns.barplot(x='Name', y='value', hue='Resource', data=wide_df)
    plt.xlabel('Name')
    plt.title("Servers")
    plt.show()


if __name__ == "__main__":
    files = [
        '../../models/basic.model',
        '../../models/big_small.model'
    ]
    models = []

    for file in files:
        model_name, job_dist, server_dist = load_dist(file)
        models.append(ModelDist(model_name, job_dist, 1, server_dist, 1))

    plot_job_distribution(models)
    plot_server_distribution(models)