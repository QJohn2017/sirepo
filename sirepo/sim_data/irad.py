# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import simulation_db
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def _compute_model(cls, analysis_model, data):
        return analysis_model


    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        cls._init_models(
            dm,
            (
                'dicomSettings',
            ),
        )
        if 'dicomReports' not in dm:
            dm.dicomReports = [
                PKDict(
                    id=1,
                    dicomPlane='t',
                ),
                PKDict(
                    id=2,
                    dicomPlane='s',
                ),
                PKDict(
                    id=3,
                    dicomPlane='c',
                ),
            ]

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        return [r]

    @classmethod
    def _lib_file_basenames(cls, data):
        return []
