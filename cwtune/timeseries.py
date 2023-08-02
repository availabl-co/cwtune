from collections import deque
from datetime import datetime, timedelta, timezone
import math
import click
def zero_pad(data, period, start, end):
    """Pad the data with zeros for missing values."""
    data_dict = {}

    for timestamp, value in data:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
        data_dict[timestamp] = value

    current_time = start
    while current_time <= end:
        if current_time not in data_dict:
            data_dict[current_time] = 0
        current_time += timedelta(minutes=period)

    data = sorted(data_dict.items(), key=lambda x: x[0])
    return data


def eval(value, threshold, alarm_type):
    """Evaluate the value against the threshold."""
    if alarm_type.is_gt():
        return value > threshold
    elif alarm_type.is_lt():
        return value < threshold


def get_breaches(data, threshold, alarm_type, window_size, time_threshold):
    """Identify the start and end of each continuous breach of the threshold."""

    # iterate over the data using a sliding window
    breaches = []
    window = []

    for timestamp, value in data:
        window.append((timestamp, value))

        # remove values that are outside of the window
        while window and window[0][0] < timestamp - timedelta(minutes=window_size):
            window.pop(0)

        # check if the window contains more than time_threshold breaches
        num_breaches = 0
        for w in window:
            if eval(w[1], threshold, alarm_type):
                num_breaches += 1

        if num_breaches >= time_threshold:
            # check if we are already in a breach
            if breaches and breaches[-1]['status'] == 'open':
                breaches[-1]['end'] = timestamp
                breaches[-1]['values'].append(value)
            else:
                breaches.append({'start': timestamp, 'end': timestamp, 'status': 'open', 'values': [value]})
        else:
            # check if we are already in a breach
            if breaches and breaches[-1]['status'] == 'open':
                breaches[-1]['end'] = timestamp
                breaches[-1]['status'] = 'closed'

    return breaches

def longest_breach(breaches):
    """Return the length of the longest breach."""
    longest_breach = timedelta(seconds=0)
    for breach in breaches:
        if breach['end'] - breach['start'] > longest_breach:
            longest_breach = breach['end'] - breach['start']
    return longest_breach

class ThresholdAdjustment:
    MIN_WINDOW_SIZE = 1
    MAX_WINDOW_SIZE = 60

    def __init__(self, threshold, breaches, data, alarm_type, window_size):
        self.threshold = threshold
        self.breaches = breaches
        self.data = data
        self.alarm_type = alarm_type
        self.window_size = window_size
        self.threshold_history = [threshold]

    def _recalculate_breaches(self):
        self.breaches = get_breaches(
            self.data,
            self.threshold,
            self.alarm_type,
            self.window_size,
            math.ceil(self.window_size / 2),
        )

    def update_threshold(self, candidate, action):
        if candidate < 0:
            click.echo(f"Threshold cannot be {action} further")
            return False
        self.threshold_history.append(candidate)
        self.threshold = candidate
        return True

    def decrease_sensitivity(self):
        if self.alarm_type.is_gt():

            if len(self.threshold_history) > 1:
                candidate = (self.threshold + self.threshold_history[-2])/2
            else:
                candidate = math.ceil(self.threshold * 1.1)
        elif self.alarm_type.is_lt():

            if len(self.threshold_history) > 1:
                candidate = (self.threshold + self.threshold_history[-2])/2
            else:
                candidate = math.ceil(self.threshold * 0.9)

        click.echo("Decreasing sensitivity")
        if self.update_threshold(candidate, 'decreased'):
            self._recalculate_breaches()

    def increase_sensitivity(self):        
        if self.alarm_type.is_gt():
            if self.threshold < 10:
                candidate = self.threshold - 1
            else:
                candidate = math.ceil(self.threshold * 0.9)
        elif self.alarm_type.is_lt():
            candidate = math.ceil(self.threshold * 1.1) 

        click.echo("Increasing sensitivity")
        if self.update_threshold(candidate, 'increased'):
            self._recalculate_breaches()

    def _adjust_window_size(self, delta, limit=None):
        new_duration = self.window_size + delta
        if limit and new_duration > limit:
            click.echo(f"Window size cannot be increased further")
            return
        
        if new_duration < self.MIN_WINDOW_SIZE:
            click.echo(f"Window size cannot be decreased further")
            return
        
        self.window_size = new_duration
        self._recalculate_breaches()

    def increase_window_size(self, limit=MAX_WINDOW_SIZE):
        self._adjust_window_size(1, limit)

    def decrease_window_size(self):
        self._adjust_window_size(-1)
