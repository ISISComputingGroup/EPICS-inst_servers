# Instrument Servers

[<img src="https://github.com/ISISComputingGroup/EPICS-inst_servers/actions/workflows/lint-and-test-nightly.yml/badge.svg">](https://github.com/ISISComputingGroup/EPICS-inst_servers/actions/workflows/lint-and-test-nightly.yml)

Channel access servers which help run the instrument. They are written in python and share some code. Many are based on [pcaspy](https://pypi.org/project/pcaspy/).

Contains:

1. [Archive Access](https://github.com/ISISComputingGroup/ibex_developers_manual/wiki/Logging-from-the-archive)
1. [Blocks Server](https://github.com/ISISComputingGroup/ibex_developers_manual/wiki/BlockServer)
1. [Database Server](https://github.com/ISISComputingGroup/ibex_developers_manual/wiki/The-DatabaseServer)
1. [Reflectometry Server](https://github.com/ISISComputingGroup/ibex_developers_manual/wiki/Reflectometers)

For more details see the [developer wiki](https://github.com/ISISComputingGroup/ibex_developers_manual/wiki//System-components)

To run tests use `pytest`
