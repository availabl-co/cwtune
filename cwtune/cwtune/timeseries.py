from datetime import datetime, timedelta, timezone

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
    if alarm_type == 'gt':
        return value > threshold
    elif alarm_type == 'lt':
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
