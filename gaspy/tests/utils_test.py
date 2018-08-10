''' Tests for the `utils` submodule '''

__author__ = 'Kevin Tran'
__email__ = 'ktran@andrew.cmu.edu'

# Modify the python path so that we find/use the .gaspyrc.json in the testing
# folder instead of the main folder
import os
os.environ['PYTHONPATH'] = '/home/GASpy/gaspy/tests:' + os.environ['PYTHONPATH']

# Things we're testing
from ..utils import find_adsorption_sites, \
    unfreeze_dict, \
    encode_atoms_to_hex, \
    decode_hex_to_atoms, \
    encode_atoms_to_trajhex, \
    decode_trajhex_to_atoms, \
    save_luigi_task_run_results, \
    evaluate_luigi_task

# Things we need to do the tests
import pytest
import pickle
import numpy as np
import numpy.testing as npt
import luigi
from luigi.parameter import _FrozenOrderedDict
from . import test_cases
from ..utils import read_rc

REGRESSION_BASELINES_LOCATION = '/home/GASpy/gaspy/tests/regression_baselines/utils/'
TASKS_OUTPUTS_LOCATION = read_rc('gasdb_path')


@pytest.mark.baseline
@pytest.mark.parametrize('slab_atoms_name',
                         ['AlAu2Cu_210.traj',
                          'CoSb2_110.traj',
                          'Cu_211.traj',
                          'FeNi_001.traj',
                          'Ni4W_001.traj',
                          'Pt12Si5_110.traj'])
def test_to_create_adsorption_sites(slab_atoms_name):
    atoms = test_cases.get_slab_atoms(slab_atoms_name)
    sites = find_adsorption_sites(atoms)

    file_name = REGRESSION_BASELINES_LOCATION + 'sites_for_' + slab_atoms_name.split('.')[0] + '.pkl'
    with open(file_name, 'wb') as file_handle:
        pickle.dump(sites, file_handle)
    assert True


@pytest.mark.parametrize('slab_atoms_name',
                         ['AlAu2Cu_210.traj',
                          'CoSb2_110.traj',
                          'Cu_211.traj',
                          'FeNi_001.traj',
                          'Ni4W_001.traj',
                          'Pt12Si5_110.traj'])
def test_find_adsorption_sites(slab_atoms_name):
    '''
    Check out `.learning_tests.pymatgen_test._get_sites_for_standard_structure`
    to see what pymatgen gives us. Our `gaspy.utils.find_adsorption_sites` simply gives us
    the value of that object when the key is 'all'.
    '''
    atoms = test_cases.get_slab_atoms(slab_atoms_name)
    sites = find_adsorption_sites(atoms)

    file_name = REGRESSION_BASELINES_LOCATION + 'sites_for_' + slab_atoms_name.split('.')[0] + '.pkl'
    with open(file_name, 'rb') as file_handle:
        expected_sites = pickle.load(file_handle)

    npt.assert_allclose(np.array(sites), np.array(expected_sites), rtol=1e-5, atol=1e-7)


def test_unfreeze_dict():
    frozen_dict = _FrozenOrderedDict(foo='bar', alpha='omega',
                                     sub_dict0=_FrozenOrderedDict(),
                                     sub_dict1=_FrozenOrderedDict(great='googly moogly'))
    unfrozen_dict = unfreeze_dict(frozen_dict)
    _look_for_type_in_dict(type_=_FrozenOrderedDict, dict_=unfrozen_dict)


def _look_for_type_in_dict(type_, dict_):
    '''
    Recursive function that checks if there is any object type inside any branch
    of a dictionary. It does so by performing an `assert` check on every single
    value in the dictionary.

    Args:
        type_   An object type (e.g, int, float, str, etc) that you want to look for
        dict_   A dictionary that you want to parse. Can really be any object with
                the `items` method.
    '''
    # Check the current layer's values
    for key, value in dict_.items():
        assert type(value) != type_
        # Recur
        try:
            _look_for_type_in_dict(type_, value)
        except AttributeError:
            pass


@pytest.mark.parametrize('adslab_atoms_name',
                         ['CO_dissociate_Pt12Si5_110.traj',
                          'CO_top_Cu_211.traj',
                          'C_hollow_AlAu2Cu_210.traj',
                          'OH_desorb_CoSb2_110.traj',
                          'OOH_dissociate_Ni4W_001.traj',
                          'OOH_hollow_FeNi_001.traj'])
def test_encode_atoms_to_hex(adslab_atoms_name):
    '''
    This actually tests GASpy's ability to both encode and decode,
    because what we really care about is being able to successfully decode whatever
    we encode.

    This is hard-coded for adslabs. It should be able to work on bulks and slabs, too.
    Feel free to update it.
    '''
    expected_atoms = test_cases.get_adslab_atoms(adslab_atoms_name)

    hex_ = encode_atoms_to_hex(expected_atoms)
    atoms = decode_hex_to_atoms(hex_)
    assert atoms == expected_atoms


@pytest.mark.baseline
@pytest.mark.parametrize('adslab_atoms_name',
                         ['CO_dissociate_Pt12Si5_110.traj',
                          'CO_top_Cu_211.traj',
                          'C_hollow_AlAu2Cu_210.traj',
                          'OH_desorb_CoSb2_110.traj',
                          'OOH_dissociate_Ni4W_001.traj',
                          'OOH_hollow_FeNi_001.traj'])
def test_to_create_atoms_hex_encoding(adslab_atoms_name):
    '''
    This is hard-coded for adslabs. It should be able to work on bulks and slabs, too.
    Feel free to update it.
    '''
    atoms = test_cases.get_adslab_atoms(adslab_atoms_name)
    hex_ = encode_atoms_to_hex(atoms)

    file_name = REGRESSION_BASELINES_LOCATION + 'hex_for_' + adslab_atoms_name.split('.')[0] + '.pkl'
    with open(file_name, 'wb') as file_handle:
        pickle.dump(hex_, file_handle)
    assert True


@pytest.mark.parametrize('adslab_atoms_name',
                         ['CO_dissociate_Pt12Si5_110.traj',
                          'CO_top_Cu_211.traj',
                          'C_hollow_AlAu2Cu_210.traj',
                          'OH_desorb_CoSb2_110.traj',
                          'OOH_dissociate_Ni4W_001.traj',
                          'OOH_hollow_FeNi_001.traj'])
def test_decode_hex_to_atoms(adslab_atoms_name):
    '''
    This is a regression test to make sure that we can keep reading old hex strings
    and turning them into the appropriate atoms objects.

    This is hard-coded for adslabs. It should be able to work on bulks and slabs, too.
    Feel free to update it.
    '''
    file_name = REGRESSION_BASELINES_LOCATION + 'hex_for_' + adslab_atoms_name.split('.')[0] + '.pkl'
    with open(file_name, 'rb') as file_handle:
        hex_ = pickle.load(file_handle)
    atoms = decode_hex_to_atoms(hex_)

    expected_atoms = test_cases.get_adslab_atoms(adslab_atoms_name)
    assert atoms == expected_atoms


@pytest.mark.parametrize('adslab_atoms_name',
                         ['CO_dissociate_Pt12Si5_110.traj',
                          'CO_top_Cu_211.traj',
                          'C_hollow_AlAu2Cu_210.traj',
                          'OH_desorb_CoSb2_110.traj',
                          'OOH_dissociate_Ni4W_001.traj',
                          'OOH_hollow_FeNi_001.traj'])
def test_encode_atoms_to_trajhex(adslab_atoms_name):
    '''
    This actually tests GASpy's ability to both encode and decode,
    because what we really care about is being able to successfully decode whatever
    we encode.

    This is hard-coded for adslabs. It should be able to work on bulks and slabs, too.
    Feel free to update it.
    '''
    expected_atoms = test_cases.get_adslab_atoms(adslab_atoms_name)

    trajhex = encode_atoms_to_trajhex(expected_atoms)
    atoms = decode_trajhex_to_atoms(trajhex)
    assert atoms == expected_atoms


@pytest.mark.baseline
@pytest.mark.parametrize('adslab_atoms_name',
                         ['CO_dissociate_Pt12Si5_110.traj',
                          'CO_top_Cu_211.traj',
                          'C_hollow_AlAu2Cu_210.traj',
                          'OH_desorb_CoSb2_110.traj',
                          'OOH_dissociate_Ni4W_001.traj',
                          'OOH_hollow_FeNi_001.traj'])
def test_to_create_atoms_trajhex_encoding(adslab_atoms_name):
    '''
    This is hard-coded for adslabs. It should be able to work on bulks and slabs, too.
    Feel free to update it.
    '''
    atoms = test_cases.get_adslab_atoms(adslab_atoms_name)
    hex_ = encode_atoms_to_trajhex(atoms)

    file_name = REGRESSION_BASELINES_LOCATION + 'trajhex_for_' + adslab_atoms_name.split('.')[0] + '.pkl'
    with open(file_name, 'wb') as file_handle:
        pickle.dump(hex_, file_handle)
    assert True


@pytest.mark.parametrize('adslab_atoms_name',
                         ['CO_dissociate_Pt12Si5_110.traj',
                          'CO_top_Cu_211.traj',
                          'C_hollow_AlAu2Cu_210.traj',
                          'OH_desorb_CoSb2_110.traj',
                          'OOH_dissociate_Ni4W_001.traj',
                          'OOH_hollow_FeNi_001.traj'])
def test_decode_trajhex_to_atoms(adslab_atoms_name):
    '''
    This is a regression test to make sure that we can keep reading old hex strings
    and turning them into the appropriate atoms objects.

    This is hard-coded for adslabs. It should be able to work on bulks and slabs, too.
    Feel free to update it.
    '''
    file_name = REGRESSION_BASELINES_LOCATION + 'trajhex_for_' + adslab_atoms_name.split('.')[0] + '.pkl'
    with open(file_name, 'rb') as file_handle:
        trajhex = pickle.load(file_handle)
    atoms = decode_trajhex_to_atoms(trajhex)

    expected_atoms = test_cases.get_adslab_atoms(adslab_atoms_name)
    assert atoms == expected_atoms


def test_save_luigi_task_run_results():
    '''
    Instead of actually testing this function, we perform a rough
    learning test on Luigi.
    '''
    assert 'temporary_path' in dir(luigi.LocalTarget)


def test_evaluate_luigi_task():
    '''
    We made some test tasks and try to execute them here. Then we verify
    the output results of the tasks.
    '''
    # Define where/what the outputs should be
    output_file_names = ['BranchTestTask/BranchTestTask_False_1_ca4048d8e6.pkl',
                         'BranchTestTask/BranchTestTask_False_42_fedcdcbd62.pkl',
                         'BranchTestTask/BranchTestTask_True_7_498ea8eed2.pkl',
                         'RootTestTask/RootTestTask__99914b932b.pkl']
    output_file_names = [TASKS_OUTPUTS_LOCATION + '/pickles/' + file_name
                         for file_name in output_file_names]
    expected_outputs = [1, 42, 7, 'We did it!']

    # Run the tasks
    try:
        evaluate_luigi_task(RootTestTask())

        # Test that each task executed correctly
        for output_file_name, expected_output in zip(output_file_names, expected_outputs):
            with open(output_file_name, 'rb') as file_handle:
                output = pickle.load(file_handle)
            assert output == expected_output

        # Clean up, regardless of what happened during testing
        __delete_files(output_file_names)
    except: # noqa: 722
        __delete_files(output_file_names)
        raise


def __delete_files(file_names):
    ''' Helper function to try and delete some files '''
    for file_name in file_names:
        try:
            os.remove(file_name)
        except OSError:
            pass


class RootTestTask(luigi.Task):
    def requires(self):
        return [BranchTestTask(task_result=1),
                BranchTestTask(task_result=7, branch_again=True)]

    def run(self):
        save_luigi_task_run_results(self, 'We did it!')

    def output(self):
        return luigi.LocalTarget(TASKS_OUTPUTS_LOCATION + '/pickles/%s/%s.pkl'
                                 % (type(self).__name__, self.task_id))


class BranchTestTask(luigi.Task):
    task_result = luigi.IntParameter(42)
    branch_again = luigi.BoolParameter(False)

    def requires(self):
        if self.branch_again:
            return BranchTestTask()
        else:
            return

    def run(self):
        save_luigi_task_run_results(self, self.task_result)

    def output(self):
        return luigi.LocalTarget(TASKS_OUTPUTS_LOCATION + '/pickles/%s/%s.pkl'
                                 % (type(self).__name__, self.task_id))
