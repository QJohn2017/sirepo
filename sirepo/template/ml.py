# -*- coding: utf-8 -*-
u"""ML execution template.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcompat
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import csv
import numpy as np
import os
import re
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

_OUTPUT_FILE = PKDict(
    fitCSVFile='fit.csv',
    predictFile='predict.npy',
    scaledFile='scaled.npy',
    testFile='test.npy',
    trainFile='train.npy',
    validateFile='validate.npy',
)


def background_percent_complete(report, run_dir, is_running):
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
    fit_csv_file = run_dir.join(_OUTPUT_FILE.fitCSVFile)
    if fit_csv_file.exists():
        line = _read_last_csv_line(fit_csv_file)
        m = re.search(r'^(\d+)', line)
        if m and int(m.group(1)) > 0:
            data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
            max_frame = data.models.neuralNet.epochs
            res.frameCount = int(m.group(1)) + 1
            res.percentComplete = float(res.frameCount) * 100 / max_frame
    return res


def get_application_data(data, **kwargs):
    if data.method == 'compute_column_info':
        return _compute_column_info(data.dataFile)
    assert False, 'unknown get_application_data: {}'.format(data)


def prepare_sequential_output_file(run_dir, data):
    report = data['report']
    if 'fileColumnReport' in report or 'partitionColumnReport':
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if fn.exists():
            fn.remove()
            try:
                save_sequential_report_data(run_dir, data)
            except IOError:
                # the output file isn't readable
                pass


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def save_sequential_report_data(run_dir, sim_in):
    if 'fileColumnReport' in sim_in.report:
        _extract_file_column_report(run_dir, sim_in)
    elif 'partitionColumnReport' in sim_in.report:
        _extract_partition_report(run_dir, sim_in)
    elif sim_in.report == 'partitionSelectionReport':
        _extract_partition_selection(run_dir, sim_in)
    else:
        assert False, 'unknown report: {}'.format(sim_in.report)


def sim_frame(frame_args):
    if frame_args.frameReport == 'epochAnimation':
        return _epoch_animation(frame_args)
    return _fit_animation(frame_args)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _compute_column_info(dataFile):
    path = str(simulation_db.simulation_lib_dir(SIM_TYPE).join(_filename(dataFile.file)))
    if re.search(r'\.npy$', path):
        return _compute_numpy_info(path)
    return _compute_csv_info(path)


def _compute_csv_info(path):
    res = PKDict(
        hasHeaderRow=True,
        rowCount=0,
    )
    row = None
    with open(str(path)) as f:
        for r in csv.reader(f):
            if not row:
                row = r
            res.rowCount += 1
    if not row:
        return PKDict(
            error='Invalid CSV file: no columns detected'
        )
    # csv file may or may not have column names
    # if any value in the first row is numeric, assume no headers
    if len(list(filter(lambda x: template_common.NUMERIC_RE.search(x), row))):
        row = ['column {}'.format(i + 1) for i in range(len(row))]
        res.hasHeaderRow = False
    res.header = row
    res.inputOutput = ['none' for i in range(len(row))]
    return res


def _compute_numpy_info(path):
    #TODO(pjm): compute column info from numpy file
    assert False, 'not implemented yet'


def _epoch_animation(frame_args):
    #TODO(pjm): improve heading text
    header = ['epoch', 'loss', 'val_loss']
    path = str(frame_args.run_dir.join(_OUTPUT_FILE.fitCSVFile))
    v = np.genfromtxt(path, delimiter=',', skip_header=1)
    if len(v.shape) == 1:
        v.shape = (v.shape[0], 1)
    return _report_info(
        v[:, 0],
        [PKDict(
            points=v[:, i].tolist(),
            label=header[i],
        ) for i in (1, 2)],
    ).update(PKDict(
        x_label=header[0],
    ))


def _extract_column(run_dir, sim_in, idx):
    y = _read_file_column(run_dir, 'scaledFile', idx)
    return np.arange(0, len(y)), y


def _extract_file_column_report(run_dir, sim_in):
    idx = sim_in.models[sim_in.report].columnNumber
    x, y = _extract_column(run_dir, sim_in, idx)
    _write_report(
        x,
        [_plot_info(y)],
        sim_in.models.columnInfo.header[idx],
    )


def _extract_partition_report(run_dir, sim_in):
    idx = sim_in.models[sim_in.report].columnNumber
    d = PKDict(
        train=_read_file_column(run_dir, 'trainFile', idx),
        test=_read_file_column(run_dir, 'testFile', idx),
        validate=_read_file_column(run_dir, 'validateFile', idx),
    )
    r = []
    for name in d:
        _update_range(r, d[name])
    plots = []
    for name in d:
        x, y = _histogram_plot(d[name], r)
        plots.append(_plot_info(y, name))
    _write_report(
        x,
        plots,
        title=sim_in.models.columnInfo.header[idx],
    )


def _extract_partition_selection(run_dir, sim_in):
    # return report with input0 and output0
    info = sim_in.models.columnInfo
    in_idx = info.inputOutput.index('input')
    out_idx = info.inputOutput.index('output')
    x, y = _extract_column(run_dir, sim_in, in_idx)
    _, y2 = _extract_column(run_dir, sim_in, out_idx)
    _write_report(
        x,
        [
            _plot_info(y, info.header[in_idx]),
            _plot_info(y2, info.header[out_idx]),
        ],
    )


def _filename(name):
    return _SIM_DATA.lib_file_name_with_model_field('dataFile', 'file', name)


def _fit_animation(frame_args):
    idx = int(frame_args.columnNumber)
    frame_args.histogramBins = 30
    info = frame_args.sim_in.models.columnInfo
    header = []
    for i in range(len(info.inputOutput)):
        if info.inputOutput[i] == 'output':
            header.append(info.header[i])
    return template_common.heatmap(
        [
            _read_file(frame_args.run_dir, _OUTPUT_FILE.predictFile)[:, idx],
            _read_file(frame_args.run_dir, _OUTPUT_FILE.testFile)[:, idx],
        ],
        frame_args,
        PKDict(
            x_label='',
            y_label='',
            title=header[idx],
            hideColorBar=True,
        ),
    )


def _generate_parameters_file(data):
    report = data.get('report', '')
    res, v = template_common.generate_parameters_file(data)
    v.dataFile = _filename(data.models.dataFile.file)
    v.update(_OUTPUT_FILE).update(
        layerImplementationNames=_layer_implementation_list(data),
        neuralNetLayers=data.models.neuralNet.layers,
        inputDim=data.models.columnInfo.inputOutput.count('input'),
    )
    v.columnTypes = '[' + ','.join([ "'" + v + "'" for v in data.models.columnInfo.inputOutput]) + ']'
    res += template_common.render_jinja(SIM_TYPE, v, 'scale.py')
    if 'fileColumnReport' in report or report == 'partitionSelectionReport':
        return res
    v.hasTrainingAndTesting = v.partition_section0 == 'train_and_test' \
        or v.partition_section1 == 'train_and_test' \
        or v.partition_section2 == 'train_and_test'
    res += template_common.render_jinja(SIM_TYPE, v, 'partition.py')
    if 'partitionColumnReport' in report:
        res += template_common.render_jinja(SIM_TYPE, v, 'save-partition.py')
        return res
    res += template_common.render_jinja(SIM_TYPE, v, 'build-model.py')
    res += template_common.render_jinja(SIM_TYPE, v, 'train.py')
    return res


def _histogram_plot(values, vrange):
    hist = np.histogram(values, bins=20, range=vrange)
    x = []
    y = []
    for i in range(len(hist[0])):
        x.append(hist[1][i])
        x.append(hist[1][i + 1])
        y.append(hist[0][i])
        y.append(hist[0][i])
    x.insert(0, x[0])
    y.insert(0, 0)
    return x, y


def _layer_implementation_list(data):
    res = {}
    for layer in data.models.neuralNet.layers:
        res[layer.layer] = 1
    return res.keys()


def _plot_info(y, label=''):
    return PKDict(points=list(y), label=label)


def _read_file(run_dir, filename):
    res = np.load(str(run_dir.join(filename)))
    if len(res.shape) == 1:
        res.shape = (res.shape[0], 1)
    return res


def _read_file_column(run_dir, name, idx):
    return _read_file(run_dir, _OUTPUT_FILE[name])[:, idx]


def _read_last_csv_line(path):
    # for performance, don't read whole file if only last line is needed
    try:
        with open(str(path), 'rb') as f:
            f.readline()
            f.seek(-2, os.SEEK_END)
            while f.read(1) != b'\n':
                f.seek(-2, os.SEEK_CUR)
            return pkcompat.from_bytes(f.readline())
    except IOError:
        return ''


def _report_info(x, plots, title=''):
    return PKDict(
        title=title,
        x_range=[float(min(x)), float(max(x))],
        y_label='',
        x_label='',
        x_points=list(x),
        plots=plots,
        y_range=template_common.compute_plot_color_and_range(plots),
    )


def _update_range(vrange, values):
    minv = min(values)
    maxv = max(values)
    if not len(vrange):
        vrange.append(minv)
        vrange.append(maxv)
        return
    if vrange[0] > minv:
        vrange[0] = minv
    if vrange[1] < maxv:
        vrange[1] = maxv


def _write_report(x, plots, title=''):
    template_common.write_sequential_result(_report_info(x, plots, title))
