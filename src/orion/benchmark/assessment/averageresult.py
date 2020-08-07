import importlib
from collections import defaultdict

from orion.benchmark.base import BaseAssess
from tabulate import tabulate
from orion.benchmark import Benchmark
import pandas as pd
import plotly.express as px
import numpy as np


class AverageResult(BaseAssess):
    """
    For each algorithm, run fixed number of Experiment, average the performance of trials for the same algorithm
    at the same trial sequence order.
    For the performance of trials in an Experiment, instead using the actual trial objective value, here we use the
    best objective value in the same Experiment until the particular trial.
    """

    def __init__(self, algorithms, task, benchmark, average_num=2):
        """
        - build assess object
        - build task object (from db[existing], or from config[new])
        """

        # TODO: task can be an object instead of package.class
        mod_str, _sep, class_str = task.rpartition('.')
        module = importlib.import_module(mod_str)
        self.task_class = getattr(module, class_str)
        self.algorithms = algorithms
        self.benchmark = benchmark

        self.tasks = []

        self.task_num = average_num

    def execute(self):
        """
        - run the tasks
        - there may be needs to run the task multiple times (such as when assess average performance)
        :return:
        """

        if isinstance(self.benchmark, Benchmark):
            task_prefix = self.benchmark.name
        else:
            task_prefix = self.benchmark

        for task_index in range(self.task_num):
            for algo_index, algorithm in enumerate(self.algorithms):

                if isinstance(algorithm, dict):
                    algorithm_name = algorithm.keys()[0]
                else:
                    algorithm_name = algorithm

                task_name = task_prefix + '_' + self.__class__.__name__ + \
                            '_' + self.task_class.__name__ + '_' + \
                            str(task_index) + '_' + str(algo_index);
                task_inst = self.task_class(task_name, algorithm, assess=self)
                task_inst.run()

                self.tasks.append((algorithm_name, task_index, task_inst))

    def status(self):
        """
        - get the overall status of the assess, like how many tasks to run and the status of each task(experiment)
        [
          {
            'algorithm': 'random',
            'assessment': 'AverageResult',
            'completed': 1,
            'experiments': 1,
            'task': 'RosenBrock',
            'trials': 10
          },
          {
            'algorithm': 'tpe',
            'assessment': 'AverageResult',
            'completed': 1,
            'experiments': 1,
            'task': 'RosenBrock',
            'trials': 10
          }
        ]
        :return:
        """
        algorithm_tasks = {}
        for task_info in self.tasks:

            algorithm_name, task_index, task = task_info
            state = task.status()
            if algorithm_tasks.get(algorithm_name, None) is None:
                task_state = {'algorithm': state['algorithm'], 'experiments': 0,
                              'assessment': self.__class__.__name__, 'task': self.task_class.__name__,
                              'completed': 0, 'trials' : 0}
            else:
                task_state = algorithm_tasks[algorithm_name]

            task_state['experiments'] = task_state['experiments'] + len(state['experiments'])

            is_done = 0
            trials_num = 0
            for exp in state['experiments']:
                if exp['is_done']:
                    is_done += 1
                trials_num += sum([len(value) for value in exp['trials'].values()])

            task_state['trials'] = task_state['trials'] + trials_num
            task_state['completed'] = task_state['completed'] + is_done

            algorithm_tasks[algorithm_name] = task_state

        assess_status = list(algorithm_tasks.values())

        return assess_status

    def result(self):
        """
        -  json format of the result
        :return:
        """
        pass

    def display(self, notebook=False):
        """
        - define the visual charts of the assess, based on the task performance output
        :return:
        """
        best_evals = defaultdict(list)
        algorithm_exp_trials = defaultdict(list)
        for task_info in self.tasks:

            algorithm_name, task_index, task = task_info

            experiments = task.performance()
            for exp in experiments:
                stats = exp.stats
                best_evals[algorithm_name].append(stats['best_evaluation'])

                trials = list(filter(lambda trial: trial.status == 'completed', exp.fetch_trials()))
                exp_trails = self._build_exp_trails(trials)
                algorithm_exp_trials[algorithm_name].append(exp_trails)

        self._display_table(best_evals, notebook)
        self._display_plot(algorithm_exp_trials)

    def _display_plot(self, algorithm_exp_trials):

        algorithm_averaged_trials = {}
        plot_tables = []
        for algo, sorted_trails in algorithm_exp_trials.items():
            data = np.array(sorted_trails).transpose().mean(axis=-1)
            algorithm_averaged_trials[algo] = data
            df = pd.DataFrame(data, columns=['objective'])
            df['algorithm'] = algo
            plot_tables.append(df)

        df = pd.concat(plot_tables)
        title = 'Assessment {} over Task {}'.format(self.__class__.__name__, self.task_class.__name__)
        fig = px.line(df, y='objective', color='algorithm', title=title)
        fig.show()

    def _display_table(self, best_evals, notebook):

        algorithm_tasks = {}
        for algo, evals in best_evals.items():
            evals.sort()
            best = evals[0]
            average = sum(evals) / len(evals)

            algorithm_tasks[algo] = {'Assessment': self.__class__.__name__, 'Task': self.task_class.__name__}
            algorithm_tasks[algo]['Algorithm'] = algo
            algorithm_tasks[algo]['Average Evaluation'] = average
            algorithm_tasks[algo]['Best Evaluation'] = best
            algorithm_tasks[algo]['Experiments Number'] = len(evals)

        if notebook:
            from IPython.display import HTML, display
            display(HTML(tabulate(list(algorithm_tasks.values()), headers='keys', tablefmt='html', stralign='center',
                                  numalign='center')))
        else:
            table = tabulate(list(algorithm_tasks.values()), headers='keys', tablefmt='grid', stralign='center',
                             numalign='center')
            print(table)

    def _build_exp_trails(self, trials):
        data = [[trial.submit_time,
                 trial.objective.value] for trial in trials]
        sorted(data, key=lambda x: x[0])

        result = []
        smallest = np.inf
        for idx, objective in enumerate(data):
            if smallest > objective[1]:
                smallest = objective[1]
                result.append(objective[1])
            else:
                result.append(smallest)
        return result

    def register(self):
        """
        register assess object into db
        :return:
        """
        pass