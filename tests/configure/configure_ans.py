class configureAnswers:
    envName: str
    cfg_location: str
    workingHours: bool
    ActiveLimit: int
    working: bool
    plantName: str
    wateringDuration: int
    wateringInterval: str

    def __init__(self, env_name, cfg_loc, work_hours, active_lim, working, plant_name, watering_dur, watering_interval):
        self.envName = env_name
        self.cfg_location = cfg_loc
        self.workingHours = work_hours
        self.ActiveLimit = active_lim
        self.working = working
        self.plantName = plant_name
        self.wateringDuration = watering_dur
        self.wateringInterval = watering_interval
