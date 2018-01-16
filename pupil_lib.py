import sys
import os
cwd = os.getcwd()

from core.plib_parser import PLibParser
from core.utilities.MPLogger import MultiProcessingLog
from core.utilities.utilities import *
from core.workers.dataset_worker import PLibDatasetWorker
from core.workers.processors.xdfloader_processor import XdfLoaderProcessor
from dependencies.xdf.Python.xdf import load_xdf
from core.utilities.config_store import ConfigStore
from core.data_container import PupilDatasets

import threading
from threading import Thread
import numpy as np
import time
import datetime
import json
import ast

def pupil_old_load(dataset, test_dir, data_num=0):
    # logger.send('INFO', 'Loading eye 0 for ' + dataset['dir'])
    split_name = test_dir.split('|')
    if len(split_name) == 1:
        test_dir = split_name[0].replace('\\\\', '\\')
        name = 'dataset' + str(data_num).replace('\\\\', '\\')
    else:
        test_dir = split_name[1].replace('\\\\', '\\')
        name = split_name[0].replace('\\\\', '\\')
    dataset['dir'] = test_dir
    dataset['dataset_name'] = name

    print(dataset)

    dataset = dict( name='',
    eye0={
        'data': [],
        'timestamps': [],
        'srate': 0,
    }, eye1={
        'data': [],
        'timestamps': [],
        'srate': 0,
    }, gaze_x={
        'data': [],
        'timestamps': [],
        'srate': 0
    }, markers={
        'timestamps': [],
        'eventnames': [],
    },
        merged=0,
        dir=test_dir,
        custom_data=False,
        dataset_name=name
    )

    dataset['eye0']['data'] = np.genfromtxt(os.path.join(test_dir, 'pupil_eye0_diams.csv'), delimiter=',')
    dataset['eye0']['timestamps'] = np.genfromtxt(os.path.join(test_dir, 'pupil_eye0_ts.csv'), delimiter=',')
    dataset['eye0']['data'], dataset['eye0']['timestamps'] = custom_interval_upsample(
        dataset['eye0']['data'],
        dataset['eye0']['timestamps'],
        0.01)
    dataset['eye0']['srate'] = PupilLibLoader.pupil_srate(dataset['eye0']['data'], dataset['eye0']['timestamps'])

    # logger.send('INFO', 'Loading eye 1 for ' + dataset['dir'], os.getpid(), threading.get_ident())
    dataset['eye1']['data'] = np.genfromtxt(os.path.join(test_dir, 'pupil_eye1_diams.csv'), delimiter=',')
    dataset['eye1']['timestamps'] = np.genfromtxt(os.path.join(test_dir, 'pupil_eye1_ts.csv'), delimiter=',')
    dataset['eye1']['data'], dataset['eye1']['timestamps'] = custom_interval_upsample(
        dataset['eye1']['data'],
        dataset['eye1']['timestamps'],
        0.01)
    dataset['eye1']['srate'] = PupilLibLoader.pupil_srate(dataset['eye1']['data'], dataset['eye1']['timestamps'])

    # logger.send('INFO', 'Loading markers for ' + dataset['dir'], os.getpid(), threading.get_ident())
    dataset['markers']['timestamps'] = np.genfromtxt(os.path.join(test_dir, 'markers_ts.csv'), delimiter=',')
    dataset['merged'] = 0
    dataset['markers']['eventnames'] = np.genfromtxt(os.path.join(test_dir, 'markers_evnames.csv'), delimiter=',',
                                                     dtype='str')

    return dataset


def xdf_pupil_load(dataset, xdf_file_and_name, data_num=0):
    name_list = dataset['dataname_list']
    print(name_list)

    # Split the dataset name from the path and store it
    # for later.
    split_list = xdf_file_and_name.split('|')
    if len(split_list) == 1:
        xdf_file = split_list[0]
        name = 'dataset' + str(data_num)
    else:
        xdf_file = split_list[1]
        name = split_list[0]
    dataset['dir'] = xdf_file
    dataset['dataset_name'] = name

    xdf_data = load_xdf(xdf_file, dejitter_timestamps=False)

    markers_stream = None
    eye0_stream = None
    eye1_stream = None
    gaze_stream = None

    # Data structures are all over the place
    # so these checks are necessary.
    for entry in xdf_data:
        if type(entry) == list:
            for i in entry:
                if type(i) == dict:
                    if 'info' in i:
                        print("type of i['info']: " + str(type(i['info'])))
                        print('i[info][name]: ' + str(i['info']['name']))
                        if i['info']['name'][0] == 'Gaze Primitive Data':
                            gaze_stream = i
                        elif i['info']['name'][0] == 'Pupil Primitive Data - Eye 1':
                            eye1_stream = i
                        elif i['info']['name'][0] == 'Pupil Primitive Data - Eye 0':
                            eye0_stream = i
                        elif i['info']['name'][0] == 'Markers':
                            markers_stream = i

    custom_data = False
    for a_name in name_list:
        if a_name != 'eye0' and a_name != 'eye1':
            custom_data = True

    data_entries = {
        'eye1': eye1_stream,
        'eye0': eye0_stream,
        'gaze_x': gaze_stream,
        'gaze_y': gaze_stream,
        'marks': markers_stream,

        'all': {
            'eye1': eye1_stream,
            'eye0': eye0_stream,
            'gaze': gaze_stream,
            'marks': markers_stream,
        }
    }

    xdf_processor = XdfLoaderProcessor()
    xdf_transforms = xdf_processor.transform.all
    all_data = {}
    print('name list: ' + str(name_list))
    for a_data_name in name_list:
        print('a_data_name: ' + a_data_name)
        funct_list = xdf_processor.data_name_to_function(a_data_name)
        results = {}
        for func in funct_list:
            if func['fn_name'] in xdf_transforms:
                config = func['config']

                def no_none_in_config(c):
                    none_in_config = True
                    for el in c:
                        if isinstance(el, str) and isinstance(c[el], dict):
                            none_in_config = no_none_in_config(c[el])
                        elif isinstance(el, str) and c[el] is None:
                            none_in_config = False
                    return none_in_config

                # If this function does not depend on previous
                # functions.
                if no_none_in_config(config):
                    results[func['field']] = xdf_transforms[func['fn_name']](data_entries[a_data_name], config)
                else:

                    def recurse_new_config(old_config, res):
                        new_config = old_config
                        for elem in old_config:
                            if isinstance(elem, str) and old_config[elem] is None:
                                if elem in res:
                                    new_config[elem] = res[elem]
                                else:
                                    raise Exception("Error: Couldn't find field " + elem)

                            elif isinstance(elem, str) and isinstance(old_config[elem], dict):
                                new_config[elem] = recurse_new_config(old_config[elem], res)
                        return new_config

                    config = recurse_new_config(config, results)
                    results[func['field']] = xdf_transforms[func['fn_name']](data_entries[a_data_name], config)
            else:
                raise Exception("Error: Couldn't find function " + func['fn_name'] + " in the XDF Processor.")

        test_pass = xdf_transforms['test_results'](results, a_data_name)
        if test_pass:
            all_data[a_data_name] = results

    # Always get the markers along with any data.
    all_data['markers'] = {
        'timestamps': xdf_transforms['get_marker_times'](markers_stream, {}),
        'eventnames': xdf_transforms['get_marker_eventnames'](markers_stream, {})
    }

    print('Results srate: ' + str(results['srate']))

    for i in markers_stream['time_series']:
        print('marks_print: ' + str(i))
    for i in markers_stream['time_stamps']:
        print('marks_time_print: ' + str(i))

    dataset['custom_data'] = custom_data

    #print(str(type(gaze_stream['time_series'])))
    #print(len(gaze_stream['time_series']))
    #print(gaze_stream['time_series'][0])

    # print(gaze_stream['time_series'][0][0])
    # tmp_dict = ast.literal_eval(gaze_stream['time_series'][0][0])
    # print(tmp_dict['timestamp'])

    new_dict = all_data
    for entry in dataset:
        if entry not in all_data:
            new_dict[entry] = dataset[entry]
    return new_dict


class PupilLibLoader(Thread):
    def __init__(self, config, num=0):
        Thread.__init__(self)
        self.config = config
        self.dataset_path_and_name = self.config['datasets'][num]
        self.datasets = []
        self.dataset = {}
        self.index = num

    # Returns the sampling rate of the given data.
    #   INPUT:
    #       pupil_data - The raw pupil data that was recorded.
    #       pupil_ts   - The raw timestamps from the recorded data.
    #   RETURN:
    #       srate      - The sampling rate.
    @staticmethod
    def pupil_srate(pupil_data, pupil_ts):
        return np.size(pupil_data, 0) / (np.max(pupil_ts) - np.min(pupil_ts))

    def load(self):
        self.dataset = {
            'dir': self.dataset_path_and_name,
            'custom_data': False,
            'merged': 0
        }

        # current_dir = os.getcwd()
        # if not os.path.exists(dataset['dir']):
        #    logger.send('ERROR', """Can't find directory: """ + dataset['dir'])
        #    return None

        # Making artifact directory
        # Set the directory name to the dataset name suffixed with
        # a timestamp.
        # epoch_time = str(int(time.time()))
        # artifacts_dir_name = os.path.normpath(dataset['dir']).split(os.sep)[-1] + "_" + epoch_time
        # print(artifacts_dir_name)
        # print(os.getcwd())

        print(self.dataset['dir'])
        if '.xdf' in self.dataset['dir']:
            self.dataset['dataname_list'] = self.config['data_name_per_dataset'][self.dataset_path_and_name] if \
                'data_name_per_dataset' in self.config else self.config['dataname_list']
            self.dataset = xdf_pupil_load(self.dataset, self.dataset['dir'], data_num=self.index)
        else:
            self.dataset = pupil_old_load(self.dataset, self.dataset['dir'], data_num=self.index)
        return self.dataset

    def run(self):
        self.load()


class PupilLibRunner(object):
    def __init__(self, config=None):
        self.config = config

        if self.config:
            ConfigStore.set_instance(config)
            self.loader = PupilLibLoader(config)
            self.logger = MultiProcessingLog.set_logger_type(self.config['logger'])
        else:
            self.loader = None

        self.loaded_datasets = []
        self.proc_datasets = {}
        self.proc_data = {}
        self.data_store = None

    def set_config(self, config):
        if config:
            self.config = config
            ConfigStore.set_instance(config)
            self.loader = PupilLibLoader(config)
            self.logger = MultiProcessingLog.set_logger_type(self.config['logger'])


    '''
        Load the given datasets into the runner.
    '''
    def load(self):
        self.load_datasets()

    def get_datasets(self):
        return self.loaded_datasets

    def load_datasets(self):
        self.logger.send('INFO', 'Loading datasets...')

        if 'no_parallel' not in self.config and \
            self.config['max_workers'] >= self.config['num_datasets']:
            # Load and run datasets in parallel
            loaders = [PupilLibLoader(self.config, i) for i in range(0, self.config['num_datasets'])]
            self.logger.send('INFO', 'hello from all ' + str(datetime.datetime.now().time()), os.getpid(), threading.get_ident())
            for i in loaders:
                i.start()
            for i in loaders:
                i.join()

            self.logger.send('INFO', 'Loaded:' + str(datetime.datetime.now().time()), os.getpid(), threading.get_ident())
            for i in loaders:
                self.loaded_datasets.append(i.dataset)
        else:
            # Not loading datasets in parallel.
            loader = PupilLibLoader(self.config)
            self.logger.send('INFO', 'hello from all ' + str(datetime.datetime.now().time()), os.getpid(),
                        threading.get_ident())
            for i in range(0, self.config['num_datasets']):
                loader.dataset_path_and_name = self.config['datasets'][i]
                loader.index = i
                loader.load()
                self.loaded_datasets.append(loader.dataset)
            self.logger.send('INFO', 'Loaded:' + str(datetime.datetime.now().time()), os.getpid(), threading.get_ident())

    '''
        Run Pupil-Lib based on the configuration given through the CLI.
        This function also controls parallelism of the dataset workers.
    '''
    def run_datasets(self):
        parallel = False
        dataset_workers = {}

        def get_dir_name(ind):
            return ((self.loaded_datasets[ind]['dataset_name'] + '|') if
                                'dataset_name' in self.loaded_datasets[ind] and
                                self.loaded_datasets[ind]['dataset_name'] != '' else
                                '') + self.loaded_datasets[ind]['dir'].replace('\\\\', '\\')

        if self.config['max_workers'] > self.config['num_datasets']:
            parallel = True
            for i in range(0, len(self.loaded_datasets)):
                dataset_worker = PLibDatasetWorker(self.config, self.loaded_datasets[i])

                dir_name = get_dir_name(i)
                dataset_workers[dataset_worker.dataset['dataset_name']] = dataset_worker
                dataset_workers[dataset_worker.dataset['dataset_name']].setName(dir_name)
                dataset_workers[dataset_worker.dataset['dataset_name']].start()
                self.proc_datasets[dataset_worker.dataset['dataset_name']] = {}
        else:
            dataset_worker = PLibDatasetWorker(self.config)
            for i in range(0, len(self.loaded_datasets)):
                dataset_worker.dataset = self.loaded_datasets[i]
                dir_name = get_dir_name(i)
                dataset_worker.setName(dir_name)
                dataset_worker.run()
                print('dataset_name')
                print(dataset_worker.dataset['dataset_name'])
                print(dir_name)
                self.proc_datasets[dataset_worker.dataset['dataset_name']] = {}
                self.proc_datasets[dataset_worker.dataset['dataset_name']] = dataset_worker.proc_dataset_data

        if parallel:
            for i in dataset_workers:
                dataset_workers[i].join()
            for i in range(0, len(self.loaded_datasets)):
                dir_name = get_dir_name(i)
                self.proc_datasets[self.loaded_datasets[i]['dataset_name']] = \
                    dataset_workers[self.loaded_datasets[i]['dataset_name']].proc_dataset_data

        self.proc_data = {
            'config': self.config,
            'datasets': self.proc_datasets
        }

    def build_datastore(self):
        if self.data_store is None:
            print('Loading data structure.')
            data_struct = PupilDatasets(self.config, self.proc_data)
            data_struct.load()
            self.data_store = data_struct
        return self.data_store

    def build_config_from_processed(self, processed_path=None):
        # Get data file(s)
        # Get config from data file and build
        # up the data structure.
        if processed_path is None:
            raise Exception('Error: Processed dataset path is none.')

        # Open the file, set config and proc data, then
        # build the data structure.
        self.build_datastore()

    def run_dataset(self, ind):
        dataset_worker = PLibDatasetWorker(self.config, self.loaded_datasets[ind])
        dataset_worker.run()

    # Gets and sets the build config depending on how and what we
    # want to process.
    def get_build_config(self, yaml_path=None, processed_path=None):
        build_config = {}
        plib_parser = PLibParser()

        if yaml_path:
            plib_parser.build_config_from_yaml(args=None, yaml_path=yaml_path)
            build_config = plib_parser.get_worker_count()
        elif processed_path:
            print('Processed not implemented yet')
            self.build_config_from_processed(processed_path)
        else:
            # Parse CLI options.
            parser = plib_parser.get_parser()
            parser.print_help()
            options = parser.parse_args()

            # Build run configuration.
            plib_parser.build_config(options)
            build_config = plib_parser.get_worker_count()

        self.set_config(build_config)
        return build_config

    # Run the runner to get the data epoched.
    # This can be used in scripts if new data is being loaded
    # through the get_build_config(...) function.
    # Otherwise, *Processor classes and their functions or
    # your own custom functions should be used to perform
    # your own post-processing on the PLib data structure.
    def run(self):
        self.load()             # Extract
        self.run_datasets()     # Transform
        self.build_datastore()  # Load

        # After finishing, save the data that was extracted.
        if self.config['store'] is not None:
            epochtime = str(int(time.time()))
            with open(os.path.join(self.config['store'], 'datasets_' + epochtime + '.json'), 'w+') as output_file:
                json.dump(jsonify_pd(self.proc_data), output_file, indent=4, sort_keys=True)

    def finish(self):
        # Close the logger.
        print('Closing the logger...\n')
        self.logger.close()
        print('Finished closing the logger.')


def main():
    # Used to run Pupil-Lib from CLI. Alternatively,
    # this function can be used in another script that would
    # accept the same arguments as this one. (Like '--run-config').
    # This is yet another way of using this tool in user
    # scripts that analyze the data further.

    # Load the datasets and run
    plibrunner = PupilLibRunner()
    plibrunner.get_build_config()
    plibrunner.run()

    # After this the plibrunner will hold information about the datasets,
    # and it can be stored for viewing, and extra processing later.
    datastore = plibrunner.data_store
    print('Last stage')

    from matplotlib import pyplot as plt

    datastore.time_or_data = 'data'
    trigs = ['S11', 'S12', 'S13', 'S14']
    col = {'S11': 'blue', 'S12': 'r', 'S13': 'g', 'S14': 'black'}
    dat_mat = datastore.datasets['dataset1'].data_streams['eye0'].triggers['S11'].get_matrix()
    plt.figure()
    for i in dat_mat:
        print(i)
        plt.plot(i)

    datastore.data_type = 'pc'

    plt.figure()
    for i in range(len(trigs)):
        plt.subplot(2, 2, i+1)
        dat_mat = datastore.datasets['dataset2'].data_streams['eye0'].triggers[trigs[i]].get_matrix()
        for trial in dat_mat:
            plt.plot(trial)
        plt.axhline(0)
        plt.axvline(256)
        plt.axvline(768)

    plt.figure()
    for trig in trigs:
        plt.plot(np.mean(datastore.datasets['dataset2'].data_streams['eye0'].triggers[trig].get_matrix(), 0), col[trig])
    plt.axhline(0)
    plt.axvline(256)
    plt.axvline(768)

    plt.show(block=True)

    #datastore.save_csv('C:/Users/Gregory/PycharmProjects/pupil_lib_parallel_exp/', name=str(int(time.time())))

    print('Main Terminating...')
    plibrunner.finish()

if __name__ == '__main__':
    main()