class HRController:
    """
    Class to handle heart rate data processing, zone calculations,
    and related fitness metrics.
    """
    def __init__(self):
        self.zones = {}
        self.current_zone = 0
        self.resting_hr = 60
        self.max_hr = 190
        self.weight_kg = 70
        
    def calculate_zones(self, age, resting_hr, max_hr=None):
        """
        Calculate heart rate zones using the Karvonen formula.
        
        Args:
            age (int): User's age
            resting_hr (int): Resting heart rate
            max_hr (int, optional): Maximum heart rate. If None, estimated from age
            
        Returns:
            dict: Heart rate zones with min and max values
        """
        if not max_hr:
            max_hr = 220 - age
        
        hr_reserve = max_hr - resting_hr
        
        self.zones = {
            1: {"min": round(resting_hr + hr_reserve * 0.5), "max": round(resting_hr + hr_reserve * 0.6) - 1},
            2: {"min": round(resting_hr + hr_reserve * 0.6), "max": round(resting_hr + hr_reserve * 0.7) - 1},
            3: {"min": round(resting_hr + hr_reserve * 0.7), "max": round(resting_hr + hr_reserve * 0.8) - 1},
            4: {"min": round(resting_hr + hr_reserve * 0.8), "max": round(resting_hr + hr_reserve * 0.9) - 1},
            5: {"min": round(resting_hr + hr_reserve * 0.9), "max": max_hr}
        }
        
        self.resting_hr = resting_hr
        self.max_hr = max_hr
        return self.zones
    
    def get_zone(self, hr):
        """
        Determine the heart rate zone for a given heart rate value.
        
        Args:
            hr (int): Current heart rate
            
        Returns:
            int: Heart rate zone (0-5, where 0 means below zone 1)
        """
        if not self.zones:
            return 0
        
        if hr < self.zones[1]["min"]:
            return 0
        elif hr <= self.zones[1]["max"]:
            return 1
        elif hr <= self.zones[2]["max"]:
            return 2
        elif hr <= self.zones[3]["max"]:
            return 3
        elif hr <= self.zones[4]["max"]:
            return 4
        else:
            return 5
            
    def calculate_wattage(self, hr, weight=70):
        """
        Rough estimate of wattage based on heart rate.
        
        Args:
            hr (int): Current heart rate
            weight (float, optional): User's weight in kg
            
        Returns:
            int: Estimated power output in watts
        """
        if hr < self.resting_hr:
            return 0
        
        # Very simplified calculation - for demonstration only
        # A more accurate model would consider VO2max, lactate threshold, etc.
        hr_reserve_used = (hr - self.resting_hr) / (self.max_hr - self.resting_hr)
        base_watts = weight * 3  # Roughly 3W per kg at threshold
        return round(base_watts * hr_reserve_used)
        
    def calculate_calories(self, hr, duration_minutes, weight=70):
        """
        Rough estimate of calories burned based on heart rate and time.
        
        Args:
            hr (int): Current heart rate
            duration_minutes (float): Exercise duration in minutes
            weight (float, optional): User's weight in kg
            
        Returns:
            int: Estimated calories burned
        """
        if hr < self.resting_hr:
            return 0
            
        # MET estimations based on HR percentages
        hr_percent = hr / self.max_hr
        if hr_percent < 0.5:
            met = 2
        elif hr_percent < 0.6:
            met = 3.5  # Light activity
        elif hr_percent < 0.7:
            met = 5    # Moderate activity
        elif hr_percent < 0.8:
            met = 7    # Vigorous activity
        elif hr_percent < 0.9:
            met = 10   # Very vigorous
        else:
            met = 12   # Extremely vigorous
            
        # Calories = MET * weight in kg * duration in hours
        return round((met * weight * (duration_minutes / 60)))
        
    def calculate_recovery_time(self, workout_duration_minutes, avg_hr):
        """
        Estimate recovery time needed based on workout intensity and duration.
        
        Args:
            workout_duration_minutes (float): Duration of workout in minutes
            avg_hr (int): Average heart rate during workout
            
        Returns:
            float: Recommended recovery time in hours
        """
        # Basic formula - just for demonstration
        hr_intensity = (avg_hr - self.resting_hr) / (self.max_hr - self.resting_hr)
        
        if hr_intensity < 0.6:  # Light workout
            recovery_factor = 0.2
        elif hr_intensity < 0.75:  # Moderate workout
            recovery_factor = 0.3
        elif hr_intensity < 0.85:  # Hard workout
            recovery_factor = 0.5
        else:  # Very intense workout
            recovery_factor = 0.7
            
        # Base recovery is related to workout duration
        base_recovery_hours = workout_duration_minutes / 60
        
        # Total recovery time
        return round(base_recovery_hours * (1 + recovery_factor) * 2) / 2  # Round to nearest half hour
    
    def calculate_zone_distribution(self, hr_samples):
        """
        Calculate time distribution across heart rate zones.
        
        Args:
            hr_samples (list): List of heart rate samples
            
        Returns:
            dict: Percentage of time spent in each zone
        """
        if not hr_samples:
            return {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            
        zone_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        total_samples = len(hr_samples)
        
        for hr in hr_samples:
            zone = self.get_zone(hr)
            zone_counts[zone] += 1
            
        zone_percentages = {}
        for zone, count in zone_counts.items():
            zone_percentages[zone] = round((count / total_samples) * 100)
            
        return zone_percentages