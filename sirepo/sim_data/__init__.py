# -*- coding: utf-8 -*-
u"""Type-based simulation operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkinspect
from pykern.pkdebug import pkdp
from sirepo import simulation_db
import importlib
import inspect
import re


def get_class(type_or_data):
    """Simulation data class

    Args:
        type_or_data (str or dict): simulation type or description
    Returns:
        type: simulation data operation class
    """
    if isinstance(type_or_data, dict):
        type_or_data = type_or_data['simulationType']
    return importlib.import_module('.' + type_or_data, __name__).SimData


def template_globals(sim_type=None):
    """Initializer for templates

    Usage::
        _SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

    Args:
        sim_type (str): simulation type [calling module's basename]
    Returns:
        (class, str, object): SimData class, simulation type, and schema
    """
    c = get_class(sim_type or pkinspect.module_basename(pkinspect.caller_module()))
    return c, c.sim_type(), c.schema()


class SimDataBase(object):

    WATCHPOINT_REPORT = 'watchpointReport'

    WATCHPOINT_REPORT_RE = re.compile('^{}(\d+)$'.format(WATCHPOINT_REPORT))

    _TEMPLATE_FIXUP = 'sim_data_template_fixup'

    @classmethod
    def init_models(cls, models, names=None, dynamic=None):
        for n in names or cls.schema().model:
            cls.update_model_defaults(
                models.setdefault(n, pkcollections.Dict()),
                n,
                dynamic=dynamic,
            )

    @classmethod
    def is_watchpoint(cls, name):
        return cls.WATCHPOINT_REPORT in name

    @classmethod
    def model_defaults(cls, name):
        """Returns a set of default model values from the schema."""
        res = pkcollections.Dict()
        for f, d in cls.schema().model[name].items():
            if len(d) >= 3 and d[2] is not None:
                res[f] = d[2]
        return res

    @classmethod
    def organize_example(cls, data):
        dm = data.models
        if 'isExample' in dm.simulation and dm.simulation.isExample:
            if dm.simulation.folder == '/':
                dm.simulation.folder = '/Examples'

    @classmethod
    def schema(cls):
        return cls._memoize(simulation_db.get_schema(cls.sim_type()))

    @classmethod
    def sim_type(cls):
        return cls._memoize(pkinspect.module_basename(cls))

    @classmethod
    def template_fixup_get(cls, data):
        if data.get(cls._TEMPLATE_FIXUP):
            del data[cls._TEMPLATE_FIXUP]
            return True
        return False

    @classmethod
    def template_fixup_set(cls, data):
        data[cls._TEMPLATE_FIXUP] = True

    @classmethod
    def update_model_defaults(cls, model, name, dynamic=None):
        defaults = cls.model_defaults(name)
        if dynamic:
            defaults.update(dynamic(name))
        for f in defaults:
            if f not in model:
                model[f] = defaults[f]

    @classmethod
    def watchpoint_id(cls, report):
        m = cls.WATCHPOINT_REPORT_RE.search(report)
        if not m:
            raise RuntimeError('invalid watchpoint report name: ', report)
        return int(m.group(1))

    @classmethod
    def _memoize(cls, value):
        """Cache class method (no args)

        Example::

            @classmethod
            def something(cls):
                return cls._memoize(compute_something_once())

        Args:
            value (object): any object

        Returns:
            object: value
        """
        @classmethod
        def wrap(cls):
            return value

        setattr(
            cls,
            inspect.currentframe().f_back.f_code.co_name,
            wrap,
        )
        return value