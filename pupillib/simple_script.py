import numpy as np
import time

from pupillib.pupil_lib import script_run


def main():
    # Load the datasets and run
    plibrunner = script_run(yaml_path='C:/Users/greg/Documents/masters/preliminaries/pupil/test_yaml2.yml')

    # After this the plibrunner will hold information about the datasets,
    # and it can be stored for viewing, and extra processing later.
    datastore = plibrunner.data_store
    print('Last stage')

    from matplotlib import pyplot as plt

    datastore.time_or_data = 'data'
    trigs = ['1', '2', '3', '4']
    col = {'1': 'blue', '2': 'r', '3': 'g', '4': 'black'}


    dat_mat = datastore.datasets['dataset_finaltest'].data_streams['gaze_x'].triggers['1'].get_all_trials_matrix()
    plt.figure()
    for i in dat_mat:
        plt.subplot(2, 1, 1)
        plt.plot(np.linspace(0, 4000, num=len(i)), i)
        plt.xlabel('Time (milli-seconds)')
        plt.ylabel('X Eye Movement (gaze x)')
    #plt.axhline(0, color='r')
    plt.axvline(1000, color='r')
    plt.axvline(3000, color='r')

    dat_mat = datastore.datasets['dataset_finaltest'].data_streams['gaze_y'].triggers['1'].get_all_trials_matrix()
    plt.subplot(2, 1, 2)
    for i in dat_mat:
        plt.plot(np.linspace(0, 4000, num=len(i)), i)
        plt.xlabel('Time (milli-seconds)')
        plt.ylabel('Y Eye Movement (gaze y)')
    #plt.axhline(0, color='r')
    plt.axvline(1000, color='r')
    plt.axvline(3000, color='r')

    #datastore.data_type = 'pc'
    datastore.save_csv('C:/Users/greg/pupil-lib-python/', name=str(int(time.time())))
    plt.show(block=True)
    datastore.data_type = 'pc'

    plt.figure()
    for i in range(len(trigs)):
        plt.subplot(2, 2, i + 1)
        dat_mat = datastore.datasets['dataset_finaltest'].data_streams['eye1'].triggers[trigs[i]].get_matrix()
        for trial in dat_mat:
            plt.plot(np.linspace(0, 4000, num=len(trial)), trial)
        plt.title('Trigger: ' + trigs[i])
        if i >= 2:
            plt.xlabel('Time (milli-seconds)')
        plt.ylabel('Percent Change Diameter')
        plt.axhline(0, color='r')
        plt.axvline(1000, color='r')
        plt.axvline(3000, color='r')

    plt.figure()
    for trig in trigs:
        line_y = np.mean(datastore.datasets['dataset_finaltest'].data_streams['eye1'].triggers[trig].get_matrix(), 0)
        plt.plot(np.linspace(0, 4000, num=len(line_y)), line_y,
                 col[trig], label=trig)
    plt.legend()
    plt.xlabel('Time (milli-seconds)')
    plt.ylabel('Percent Change Diameter')
    plt.axhline(0, color='r')
    plt.axvline(1000, color='r')
    plt.axvline(3000, color='r')

    plt.show(block=True)

    datastore.save_csv('C:/Users/greg/pupil-lib-python/', name=str(int(time.time())))

    print('Main Terminating...')
    plibrunner.finish()

if __name__ == "__main__":
    main()