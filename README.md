v1.0.0: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.2589448.svg)](https://doi.org/10.5281/zenodo.2589448)
v0.1.0: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1403896.svg)](https://doi.org/10.5281/zenodo.1403896)


# Pupil-Lib Python

This library is for processing data that is obtained from the [Pupil Labs](https://pupil-labs.com/) eye tracker working in conjunction with [Lab Streaming Layer](https://github.com/sccn/labstreaminglayer) (LSL) that retrieves the needed event markers and eye tracker data. These event markers can be created anywhere and sent over the network to the Lab Recorder. The XDF file's created can then be given to this library, with a configuration file [(a YAML or .yml file)](https://github.com/gmierz/pupil-lib-python/blob/master/pupillib/resources/test_yaml1.yml), to perform trial extraction. It can be used as a command line tool, or python module import.

Once processed by this library, the trials that are returned after extraction have zero error in their length relative to what was requested - leaving only small network latencies as the cause for errors. The data is also resampled into an evenly spaced timeseries to make processing and analysis simpler. This is particularly useful when we need to deal with un-evenly sampled data streams obtained from LSL's XDF data exports or the Pupil Labs eye tracker. These streams are also synchronized by LSL on import and have a [high level of precision](https://sccn.ucsd.edu/~mgrivich/LSL_Validation.html).

The Matlab version is available here: https://github.com/gmierz/pupil-lib-matlab

## Dependencies
To have an experiment compatible with this library the following is required:
  1. Pupil Labs binocular eye tracker: https://pupil-labs.com/ .
  2. Lab Streaming Library (LSL): https://code.google.com/archive/p/labstreaminglayer/ . The version contained in 'liblsl-1.04.zip' in the downloads page is known to work with the Matlab marker inlet function.
  3. LabRecorder: ftp://sccn.ucsd.edu/pub/software/LSL/Apps/ . This version contained in 'LabRecorder-1.12c.zip' is known to work with the Pupil Labs eye tracker and produces compatible XDF files.
  4. Pupil Labs LSL Plugin: https://pupil-labs.com/blog/2016-11/pupil-plugin-for-lab-streaming-layer/ . Follow their instructions to get it working. I had to use the source code in the Lab Streaming Library repo to be able to properly produce the 'pylsl' folder. What helped the most here was running the script 'get_deps.py' which will fill the 'pylsl' folder with needed files. This can be done before or after the 'build' phase.

## Running a compatible experiment

Any experiment must use the [Lab Recorder](https://github.com/sccn/labstreaminglayer/tree/master/Apps/LabRecorder) to record all the data, the Pupil Labs LSL Relay Plugin (mentioned above) to send data from a Capture interface running on a network, and a Lab Streaming Layer outlet producing event markers (from any language) somewhere. See [here](https://github.com/gmierz/pupil-lib/blob/master/server_client/create_marker_outlet.m) for a Matlab example - use with `outlet.push_sample({'Marker Name'})` in a stimulus script. You can wait until it [has consumers](https://github.com/sccn/labstreaminglayer/blob/master/LSL/liblsl-Matlab/lsl_outlet.m#L110-L129) as well to automatically start stimuli from a Lab Recorder application.

Any experiment, in general, goes as follows:
1. Insert markers into stimulus scripts, and have it ready and waiting for consumers.
2. Start eye trackers, and Pupil Capture and prepare - ensure that the relay plugin is on.
3. Open Lab Recorder on a recording machine that is on to the same network the eye trackers and event markers are on.
4. Check boxes for all data required
    - `diameter_3d` (in mm) comes from the `Python representation`, and  `diameter` is the diameter (in pixels) uncorrected for perspective it is the only diameter available in the `Primitive data`.
    - Always remember to have the marker one selected, or the stimulus won't start if you're waiting on consumers.
    - If you're not sure what you need, take the python representation. It will result in large files, but it's also the only way to get perspective corrected diameters (or specific gaze data).
5. Start Lab Recorder when you're ready to start the experiment.

Note: There is no need to record from Pupil Capture, but you can if you still need to.

## Usage

Once you clone this library, you should run `python setup.py install` from within the directory so that you can use it in a script anywhere.
Here are some example commands:

```
cd ~
git clone https://github.com/gmierz/pupil-lib-python
cd pupil-lib-python
python setup.py install
```

After this, you will be able to use pupillib as a python module import or a command line tool with [YAML configurations](https://github.com/gmierz/pupil-lib-python/blob/master/pupillib/resources/test_yaml1.yml).

An easy way to get going after this is by using the script [pupillib/simple_script.py](https://github.com/gmierz/pupil-lib-python/blob/master/pupillib/simple_script.py) as an example to get what you need. Then change `yaml_path='resources/test_yaml1.yml'` to point to another YAML file (which could be the same file - copied or not) and modify the configuration to your experiment.

The markers that are recorded must have a type of 'Markers' to be processed. If the type is mixed with the name change `type` to `name` here:
One way is to use it is in a script with calls that resemble the `main()` function in pupil_lib.py. `yaml_path` must be defined
in the `get_build_config(yaml_path=<PATH/TO/YAML>)` call. Or if you don't need much control, `script_run(yaml_path=<PATH/TO/YAML>)`
in the same file can be used to do everything and return an PupilLibRunner object that contains the data in the field `.data_store`.

See `docs/data_container.md` for more information on the data container `.data_store` which holds all the data - `pupillib/simple_script.py` is a good example.

You can also use it through the command prompt as well with something like (this is the suggested method):

```
pupillib --run-config C:\Users\Gregory\PycharmProjects\pupil_lib_parallel_exp\resources\test_yaml1.yml`
```

Or with only this to get the arguments from a YAML configuration file (defined in the docs/ folder):

```
pupillib -D C:\Recordings\CurrentStudy\subj4\block__old41.xdf --data-names gaze_x gaze_y
 --trigger-pre-processing "{name: default}" {'name':'get_sums','config':[4]} -t S11 S12 --max-workers 1
 --tr -2 0 --logger stdout --test --testingdepth deep
```

## Data Usage

`data_container.py` shows the general structure of the data once it's finished processing, with docs in `docs/data_container.md`. Generally speaking, accessing data will be similar in all cases to what is done in `simple_script.py`.

## Marker creation

Using the Pupil Labs LSL plugin, you can create and send markers from a stimulus script in the same way that is done here:
 https://github.com/sccn/labstreaminglayer/blob/master/LSL/liblsl-Python/examples/SendStringMarkers.py

The stream can/will be saved by the Lab Recorder software and that data can then be used for processing in this library.
(For the stimulus scripts, they can be in any language that LSL offers so that markers can be created and sent).

## Examples of data that can be retrieved

These images below are from processing a dataset where a subject was looking at these stimuli:

![alt text](https://user-images.githubusercontent.com/10966989/35007458-ce26d07a-fac7-11e7-9817-1e2c3f2bfc9e.png)

Gaze data (gaze_x, and gaze_y fields) - data from when a world camera was not in use:

![alt text](https://user-images.githubusercontent.com/10966989/35007537-f99df72e-fac7-11e7-9daa-d035ca92bd42.png)

All trials across all triggers:

![alt text](https://user-images.githubusercontent.com/10966989/35007535-f97cf86c-fac7-11e7-9eab-8949a9961a7e.png)

Mean of all trials for each trigger overlaid:

![alt text](https://user-images.githubusercontent.com/10966989/35007562-121dbcf8-fac8-11e7-9acd-c14bd579fdef.png)

## Customization

This library, at it's core, only extracts trials. This is why it's main features are zero-error trial extraction, and helping with the correction of uneven sampling rates. But it uses processor files to perform any processing like percent-change calculations, and filtering. Because of this it is very simple to insert your own customized functionality before or after any part of the processing pipeline. See `pupillib/docs/pre_post_functions` for how to do this. In the near future, it will also be possible to add custom classes (extending from the processor classes) with the same decorators from a directory outside the library with an environment flag.

## Testing

Testing is done within the library itself, but it is only fully tested when `testing: True` is set in the `config` entry of a YAML configuration file. This makes it simpler to reproduce specific errors within a given dataset. There are also two test YAML files situated in `pupillib/resources`.

## Future Additions and Fixes

1. Custom class imports for processing.
2. Stronger/better CSV exporting.
3. Deprecation of all command line arguments except for `--run-config=<PATH>` for simplification purposes.
4. More documentation of data structures at the various pre/post processing levels.

## Academic Citation

There is no article to cite for this source code for the time being. However, if this code is used in any scientific publications, please consider referencing this repository by following the Zenodo badge link, and using the "cite as" entry from there:

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.2589448.svg)](https://doi.org/10.5281/zenodo.2589448)

If you need a newer release, you can let me know through an issue.

## License - GPLV3
This library is licensed under GPLV3, see here for the license: https://github.com/gmierz/pupil-lib/blob/master/LICENSE
If another type is required please contact me so that we can discuss.

Finally, as always feel free to ask any questions you may have through issues and post your issues or suggested improvements through there as well. :)
