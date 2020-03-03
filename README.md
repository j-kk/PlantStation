PlantStation
============
A little daemon to keep plants watered with Raspberry Pi

### Installation

Clone the repository and inside the directory PlantStation run
```
    pip install .
```

After that you will have 2 new programs:
- PlantStation - the plant keeper app
- PlantSetup - the configuration script

### Configuration - PlantSetup

The PlantSetup has two commands:
- config: creates environment configuration file by checking every output pin. Be aware to observe this situation
- service: creates .service file in user or global location, which enables to run PlantStation daemon as system service

### Running the PlantStation daemon
The PlantStation daemon keeps after each plant described in environment configuration file.
This file is required to perform any action.
PlantStation may run either in standalone (-s) or supervised mode.
