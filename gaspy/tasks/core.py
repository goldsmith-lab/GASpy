'''
This module houses various utility functions that we can use when working with
Luigi tasks
'''

__authors__ = ['Zachary W. Ulissi', 'Kevin Tran']
__emails__ = ['zulissi@andrew.cmu.edu', 'ktran@andrew.cmu.edu']

import os
import types
from collections import Iterable
import pickle
import warnings
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', category=DeprecationWarning)
    import luigi
from .. import utils
from ..fireworks_helper_scripts import get_launchpad

GASDB_PATH = utils.read_rc('gasdb_path')
TASKS_CACHE_LOCATION = utils.read_rc('gasdb_path') + '/pickles/'


def schedule_tasks(tasks, workers=1, local_scheduler=False):
    '''
    This light wrapping function will execute any tasks you want through the
    Luigi host that is listed in the `.gaspyrc.json` file.

    Arg:
        tasks               An iterable of `luigi.Task` instances
        workers             An integer indicating how many processes/workers
                            you want executing the tasks and prerequisite
                            tasks.
        local_scheduler     A Boolean indicating whether or not you want to
                            use a local scheduler. You should use a local
                            scheduler only when you want something done
                            quickly but dirtily. If you do not use local
                            scheduling, then we will use our Luigi daemon
                            to manage things, which should be the status
                            quo.
    '''
    luigi_host = utils.read_rc('luigi_host')
    luigi_port = utils.read_rc('luigi_port')

    # Ignore this silly Luigi warning that they're too lazy to fix
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message='Parameter '
                                '"task_process_context" with value "None" is not '
                                'of type string.')

        if local_scheduler is False:
            luigi.build(tasks, workers=workers, scheduler_host=luigi_host, scheduler_port=luigi_port)
        else:
            luigi.build(tasks, workers=workers, local_scheduler=True)


def run_task(task, force=False):
    '''
    This follows luigi logic to evaluate a task by recursively evaluating all
    requirements. This is useful for executing tasks that are typically
    independent of other tasks, e.g., populating a catalog of sites.

    This differs from `schedule_tasks` in that this function will execute the
    task manually, while `schedule_tasks` will get the Luigi daemon/scheduler
    to do it. This function should be used for debugging, testing, or if you
    know you'll spawn > 200 tasks (which Luigi schedulers are bad at handling).

    Arg:
        task    Class instance of a luigi task
        force   A boolean indicating whether or not you want to forcibly
                evaluate the task and all the upstream requirements. Useful for
                re-doing tasks that you know have already been completed.
    '''
    # Don't do anything if it's already done and we're not redoing
    if task.complete() and not(force):
        return

    else:
        # Execute prerequisite task[s] recursively
        dependencies = task.requires()
        if dependencies:
            if isinstance(dependencies, dict):
                for dep in dependencies.values():
                    if not(dep.complete()) or force:
                        run_task(dep, force)

            elif isinstance(dependencies, Iterable):
                for dep in dependencies:
                    if not(dep.complete()) or force:
                        run_task(dep, force)
            else:
                if not(dependencies.complete()) or force:
                    run_task(dependencies, force)

        # Luigi will yell at us if we try to overwrite output files. So if
        # we're foricbly redoing tasks, we need to delete the old outputs.
        if force:
            os.remove(task.output().path)

        # After prerequisites are done, run the task
        run_results = task.run()

        # If there are dynamic dependencies, then run them
        if isinstance(run_results, types.GeneratorType):
            for dependency in run_results:
                if isinstance(dependency, luigi.Task):
                    run_task(dependency)
                # Sometimes we can actually get a list of dynamic
                # dependendencies instead of one at a time. We address that
                # here.
                elif isinstance(dependency, Iterable):
                    for dep in dependency:
                        run_task(dep)


def make_task_output_object(task):
    '''
    This function will create an instance of a luigi.LocalTarget object, which
    is what the `output` method of a Luigi task should return. The main thing
    this function does for you is that it creates a target with a standardized
    location.

    Arg:
        task    Instance of a luigi.Task object
    Returns:
        target  An instance of a luigi.LocalTarget object with the `path`
                attribute set to GASpy's standard location (as defined by
                the `make_task_output_location` function)
    '''
    output_location = make_task_output_location(task)
    target = luigi.LocalTarget(output_location)
    return target


def make_task_output_location(task):
    '''
    We have a standard location where we store task outputs. This function
    will find that location for you.

    Arg:
        task    Instance of a luigi.Task that you want to find the output location for
    Output:
        file_name   String indication the full path of where the output is
    '''
    task_name = type(task).__name__
    task_id = task.task_id
    file_name = TASKS_CACHE_LOCATION + '%s/%s.pkl' % (task_name, task_id)
    return file_name


def save_task_output(task, output):
    '''
    This function is a light wrapper to save a luigi task's output. Instead of
    writing the output directly onto the output file, we write onto a temporary
    file and then atomically move the temporary file onto the output file.

    This defends against situations where we may have accidentally queued
    multiple instances of a task; if this happens and both tasks try to write
    to the same file, then the file gets corrupted. But if both of these tasks
    simply write to separate files and then each perform an atomic move, then
    the final output file remains uncorrupted.

    Doing this for more or less every single task in GASpy gots annoying, so
    we wrapped it.

    Args:
        task    Instance of a luigi task whose output you want to write to
        output  Whatever object that you want to save
    '''
    with task.output().temporary_path() as task.temp_output_path:
        with open(task.temp_output_path, 'wb') as file_handle:
            pickle.dump(output, file_handle)


def get_task_output(task):
    '''
    This function will open and return the output of a Luigi task. This
    function assumes that the `output` method of the task returns a single
    luigi.LocalTarget object.

    Arg:
        task    Instance of a luigi.Task that you want to find the output of
    Output:
        output  Whatever was saved by the task
    '''
    target = task.output()
    with open(target.path, 'rb') as file_handle:
        output = pickle.load(file_handle)
    return output


class DumpFWToTraj(luigi.Task):
    '''
    Given a FWID, this task will dump a traj file into GASdb/FW_structures for viewing/debugging
    purposes
    '''
    fwid = luigi.IntParameter()

    def run(self):
        lpad = get_launchpad()
        fw = lpad.get_fw_by_id(self.fwid)
        atoms_trajhex = fw.launches[-1].action.stored_data['opt_results'][1]

        # Write a blank token file to indicate this was done so that the entry is not written again
        with self.output().temporary_path() as self.temp_output_path:
            with open(self.temp_output_path, 'w') as fhandle:
                fhandle.write(utils.decode_trajhex_to_atoms(atoms_trajhex))

    def output(self):
        return luigi.LocalTarget(GASDB_PATH+'/FW_structures/%s.traj' % (self.fwid))
