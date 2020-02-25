import os
import subprocess

import orion.core.cli
import pytest
from orion.client import create_experiment
from orion.storage.base import get_storage


def test_script_integrity(capsys):
    """
    Verifies the example script can run in standalone via `python ...`.
    """
    script = os.path.abspath("examples/scikitlearn-iris/main.py")

    return_code = subprocess.call(["python", script, '0.1'])

    assert return_code != 2, "The example script does not exists."
    assert return_code != 1, "The example script did not terminates its execution."
    assert return_code == 0 and not capsys.readouterr().err, \
        "The example script encountered an error during its execution."


@pytest.mark.usefixtures("clean_db")
@pytest.mark.usefixtures("null_db_instances")
def test_orion_runs_script(monkeypatch, database):
    """
    Verifies Oríon can execute the example script.
    """
    script = os.path.abspath("examples/scikitlearn-iris/main.py")
    monkeypatch.chdir(os.path.dirname(os.path.abspath(__file__)))
    config = "orion_config.yaml"

    orion.core.cli.main(["hunt", "--config", config, "python", script,
                         "orion~choices([0.1])"])

    exps = list(database.experiments.find({'name': 'scikit-iris-tutorial'}))
    assert len(exps) == 1

    exp = exps[0]
    assert exp['version'] == 1
    assert len(exp['space']) == 1
    assert '/_pos_2' in exp['space']

    storage = get_storage()
    trials = storage.fetch_trials(uid=exp['_id'])
    assert len(trials) == 1

    trial = trials[0]
    assert trial.status == 'completed'
    assert trial.params['/_pos_2'] == 0.1


@pytest.mark.usefixtures("clean_db")
@pytest.mark.usefixtures("null_db_instances")
def test_script_results(monkeypatch):
    """
    Verifies the script results stays consistent (with respect to the documentation).
    """
    script = os.path.abspath("examples/scikitlearn-iris/main.py")
    monkeypatch.chdir(os.path.dirname(os.path.abspath(__file__)))
    config = "orion_config.yaml"

    orion.core.cli.main(["hunt", "--config", config, "python", script,
                         "orion~choices([0.1])"])

    experiment = create_experiment(name="scikit-iris-tutorial")
    assert 'best_evaluation' in experiment.stats
    assert experiment.stats['best_evaluation'] == 0.6666666666666667