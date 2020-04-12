import os


class configureAnswers:
    envName: str
    cfg_location: str
    workingHours: bool
    ActiveLimit: str
    working: bool
    plantName: str
    wateringDuration: str
    wateringInterval: str
    workingHoursBegin: str
    workingHoursEnd: str

    def __init__(self, env_name, cfg_loc, work_hours, active_lim, working, plant_name, watering_dur, watering_interval,
                 hours_beg, hours_end):
        self.envName = env_name
        self.cfg_location = cfg_loc
        self.workingHours = work_hours
        self.ActiveLimit = active_lim
        self.working = working
        self.plantName = plant_name
        self.wateringDuration = watering_dur
        self.wateringInterval = watering_interval
        self.workingHoursBegin = hours_beg
        self.workingHoursEnd = hours_end

    def expected_output01(self, last_time_watered, water_dur, water_interval):
        cwd = os.getcwd()
        expected_res = [cwd + f'/{self.envName}.cfg', '[GLOBAL]', f'env_name = {self.envName}',
                        f'ActiveLimit = {self.ActiveLimit}', f'[{self.plantName}]', 'gpioPinNumber = GPIO27',
                        f'lastTimeWatered = {last_time_watered}', f'plantName = {self.plantName}',
                        f'wateringDuration = {water_dur}', f'wateringInterval = {water_interval}']
        return expected_res

    def expected_output02(self, last_time_watered, water_dur, water_interval):
        cwd = os.getcwd()
        expected_res = [cwd + f'/{self.envName}.cfg', '[GLOBAL]', f'env_name = {self.envName}',
                        f'ActiveLimit = {self.ActiveLimit}', f'workingHours = {self.working}',
                        f'workingHoursBegin = {self.workingHoursBegin}', f'workingHoursEnd = {self.workingHoursEnd}',
                        f'[{self.plantName}]', 'gpioPinNumber = GPIO27', f'lastTimeWatered = {last_time_watered}',
                        f'plantName = {self.plantName}', f'wateringDuration = {water_dur}',
                        f'wateringInterval = {water_interval}']
        return expected_res

