from enum import Enum
import click
from datetime import timedelta
from terminaltables import AsciiTable
from thefuzz import fuzz
import json
import math
from .utils import create_cloudwatch_link, format_timestamp, select_range
from .aws import list_metrics, get_metric_data, create_cloudwatch_alarm, cw_client
from .timeseries import zero_pad, get_breaches, longest_breach, ThresholdAdjustment

# Define constants
WEIGHTS = {'Namespace': 0.5, 'MetricName': 0.3, 'Dimensions': 0.3}
MAX_ITERATIONS = 100
NUM_SEARCH_RESULTS = 5

def prompt_metric_search(metrics):
    """Prompts the user for a metric search and returns a selected metric."""
    click.echo('Enter a metric search eg "EC2 CPUUtilization XService"')
    while True:
        search = click.prompt('Search', type=str)
        click.echo('Select a metric from the list below')

        metrics = sorted(metrics, key=lambda metric: WEIGHTS['Namespace'] * fuzz.token_set_ratio(search, metric['Namespace']) +
                         WEIGHTS['MetricName'] * fuzz.token_set_ratio(search, metric['MetricName']) +
                         WEIGHTS['Dimensions'] * fuzz.token_set_ratio(search, json.dumps(metric['Dimensions'])), reverse=True)

        for i, metric in enumerate(metrics[:NUM_SEARCH_RESULTS]):
            click.echo(
                f"{i + 1}: {metric['Namespace']} {metric['MetricName']} {json.dumps({dimension['Name']: dimension['Value'] for dimension in metric['Dimensions']})}")

        click.echo("6: Search again")

        selected_metric = click.prompt('Please enter a number to select a metric', type=int)
        click.echo()

        if selected_metric == NUM_SEARCH_RESULTS + 1:
            continue

        if selected_metric < 1 or selected_metric > NUM_SEARCH_RESULTS:
            click.echo('Invalid selection.')
            continue

        return metrics[selected_metric - 1]


def retrieve_and_pad_data(metric, period, statistic, client):
    """Retrieves and pads metric data."""
    start, end = select_range()

    click.echo(f"Retrieving data from {format_timestamp(start)} to {format_timestamp(end)}.")

    data = get_metric_data(start, end, metric['MetricName'], metric['Namespace'], metric['Dimensions'], period, statistic, client)
    click.echo(f"Retrieved {len(data)} data points.")

    if len(data) == 0:
        click.echo("No data found.")
        return []

    data = zero_pad(data, period, start, end)
    click.echo(f"Padded data to {len(data)} data points.")
    return data, start, end


def calculate_threshold_and_breaches(data, alarm_type, window_size, max_alerts):
    """Calculates threshold and breaches for the given data."""
    # Initial values
    values = [value for timestamp, value in data]
    sum_values = sum(values)
    std_dev = sum([abs(value - sum_values / len(values))
            for value in values]) / len(values)

    if alarm_type.is_gt():
        threshold = math.ceil(sum_values / len(values) + 5 * std_dev)
    elif alarm_type.is_lt():
        threshold = max(math.ceil(sum_values / len(values) - 5 * std_dev), 1)

    breaches = get_breaches(data, threshold, alarm_type,
                            window_size, math.ceil(window_size / 2))


    # Threshold search when breaches are too many or too long
    if len(breaches) > max_alerts or longest_breach(breaches) > timedelta(days=2):
        click.echo('Starting binary search for threshold.')

        min_threshold = min(values)
        max_threshold = max(values) * 2

        for i in range(MAX_ITERATIONS):
            click.echo(
                f"Iteration {i + 1}. Evaluating threshold of {threshold}.")
            threshold = math.ceil((min_threshold + max_threshold) / 2)
            breaches = get_breaches(
                data, threshold, alarm_type, window_size, math.ceil(window_size / 2))

            if len(breaches) > max_alerts:
                min_threshold = threshold
            else:
                if longest_breach(breaches) < timedelta(days=2):
                    break
                else:
                    min_threshold = threshold
                    max_threshold = max_threshold * 2

    return threshold, breaches


def output_rating_and_adjustment(metric, data, alarm_type, threshold, window_size, breaches, start, region, statistic, period):
    """Handles output rating and adjustment based on user feedback."""

    # Create an instance of ThresholdAdjustment
    adjustment = ThresholdAdjustment(threshold, breaches, data, alarm_type, window_size)

    # Define option map
    option_map = {
        1: {
            "description": "Too many alerts",
            "action": adjustment.decrease_sensitivity,
        },
        2: {
            "description": "Too few alerts",
            "action": adjustment.increase_sensitivity,
        },
        3: {
            "description": "Too many flapping alerts",
            "action": adjustment.increase_window_size,
        },
        4: {
            "description": "Alets are too slow to trigger",
            "action": adjustment.decrease_window_size,
        },
        5: {
            "description": "Just right",
            "action": None,  # No action for this option
        },
    }

    while True:
        if adjustment.threshold > 1:
            adjustment.threshold = math.ceil(adjustment.threshold)

        click.echo(f"X {'>' if alarm_type.is_gt() else '<'} {adjustment.threshold} for {int(adjustment.window_size/2)} in {adjustment.window_size} datapoints would have triggered {len(adjustment.breaches)} alerts.")
        table_data = [['Start', 'End', 'Duration', 'Link']]

        for breach in adjustment.breaches:
            duration = breach['end'] - breach['start']
            link = create_cloudwatch_link(
                metric['Namespace'], metric['MetricName'], breach['start'],
                breach['end'], metric['Dimensions'], adjustment.threshold, region, statistic, period
            )
            table_data.append([format_timestamp(breach['start']),
                              format_timestamp(breach['end']), duration, link])

        if len(table_data) > 1:
            table = AsciiTable(table_data) 
            click.echo(table.table)
            click.echo()

        click.echo("Rate the output")
        for option, details in option_map.items():
            click.echo(f"{option}: {details['description']}")

        rating = click.prompt('Please enter a number to rate the output', type=int)
        click.echo()

        selected_option = option_map.get(rating)
        if selected_option:
            action = selected_option.get('action')
            if action:
                action()
            else:
                break

    return adjustment.threshold, adjustment.window_size


def ask_to_create_alarm(metric, threshold, alarm_type, client, statistic, period, window_size):
    """Asks the user if they want to create a CloudWatch alarm and creates it if they do."""
    if click.confirm('Create/Update an alarm for this metric?', default=True):
        create_cloudwatch_alarm(
            metric['MetricName'], metric['Namespace'], metric['Dimensions'], threshold, alarm_type,
            client, statistic=statistic, period=period, window_size=window_size
        )


def run(alarm_type, aws_profile=None, period=5, statistic='Sum', region='us-east-1', window_size=5, max_alerts=11, client=None):
    """Select threshold for CloudWatch metrics."""

    if not client:
        client = cw_client(aws_profile, region)

    try:
        metrics = list_metrics(client)
    except Exception as e:
        click.echo(f"Failed to list metrics: {e}")
        return 1  # Non-zero status code to indicate an error

    try:
        metric = prompt_metric_search(metrics)
    except Exception as e:
        click.echo(f"Failed to prompt for metric search: {e}")
        return 1

    try:
        data, start, end = retrieve_and_pad_data(metric, period, statistic, client)
    except Exception as e:
        click.echo(f"Failed to retrieve and pad data: {e}")
        return 1

    if len(data) == 0:
        return 0

    try:
        threshold, breaches = calculate_threshold_and_breaches(data, alarm_type, window_size, max_alerts)
    except Exception as e:
        click.echo(f"Failed to calculate threshold and breaches: {e}")
        return 1

    try:
        threshold, window_size = output_rating_and_adjustment(
            metric, data, alarm_type, threshold, window_size, breaches, start, region, statistic, period
        )
    except Exception as e:
        click.echo(f"Failed to adjust output based on rating: {e}")
        return 1

    try:
        ask_to_create_alarm(metric, threshold, alarm_type, client, statistic, period, window_size)
    except Exception as e:
        click.echo(f"Failed to create alarm: {e}")
        return 1

    return 0
