# -*- coding: utf-8 -*-
u"""List of features available

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
# defer all imports so *_CODES is available to testing functions


#: Codes on beta and prod; 'shadow' is unsupported on F29 for now
NON_ALPHA_CODES = frozenset((
    'elegant',
    'jspec',
    'srw',
    'synergia',
    'warppba',
    'warpvnd',
    'webcon',
    'zgoubi',
))

#: Codes on dev and alpha
ALPHA_CODES = frozenset((
    'adm',
    'flash',
    'myapp',
    'rs4pi',
    'opal',
))

#: All possible codes
ALL_CODES = NON_ALPHA_CODES.union(ALPHA_CODES)

#: Configuration
_cfg = None


def cfg():
    """global configuration

    Returns:
        dict: configurated features
    """
    global _cfg
    if not _cfg:
        _init()
    return _cfg


def for_sim_type(sim_type):
    """Get cfg for simulation type

    Args:
        sim_type (str): srw, warppba, etc.

    Returns:
        dict: merged gui global and application specific config
    """
    import pykern.pkcollections

    c = cfg()
    r = pykern.pkcollections.PKDict(**c.gui_global)
    if sim_type in c:
        r.update(pykern.pkcollections.map_items(c[sim_type]))
    return r


def _init():
    from pykern import pkconfig
    global _cfg

    @pkconfig.parse_none
    def _cfg_sim_types(value):
        res = pkconfig.parse_set(value)
        if not res:
            return tuple(_codes())
        for c in res:
            assert c in _codes(), \
                'invalid sim_type={}, expected one of={}'.format(c, _codes())
        if 'jspec' in res:
            res = set(res)
            res.add('elegant')
        return tuple(res)

    def _codes():
        return ALL_CODES if pkconfig.channel_in_internal_test() \
            else NON_ALPHA_CODES

    _cfg = pkconfig.init(
        api_modules=((), set, 'optional api modules, e.g. status'),
        gui_global=dict(
            archive_simulation=(pkconfig.channel_in_internal_test(), bool, 'Display archive simulation button')
        ),
        job=(False, bool, '[new] job execution architecture (replaces runner)'),
        jspec=dict(
            derbenevskrinsky_force_formula=(pkconfig.channel_in_internal_test(), bool, 'Include Derbenev-Skrinsky force forumla'),
        ),
        #TODO(robnagler) make sim_type config
        rs4pi_dose_calc=(False, bool, 'run the real dose calculator'),
        sim_types=(None, _cfg_sim_types, 'simulation types (codes) to be imported'),
        srw=dict(
            mask_in_toolbar=(pkconfig.channel_in_internal_test(), bool, 'Show the mask element in toolbar'),
            beamline3d=(pkconfig.channel_in_internal_test(), bool, 'Show 3D beamline plot'),
        ),
        warpvnd=dict(
            allow_3d_mode=(True, bool, 'Include 3D features in the Warp VND UI'),
            display_test_boxes=(pkconfig.channel_in_internal_test(), bool, 'Display test boxes to visualize 3D -> 2D projections'),
        ),
    )
