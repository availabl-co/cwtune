import click
from datetime import timedelta
from terminaltables import AsciiTable
from thefuzz import fuzz
import json
import math
from utils import create_cloudwatch_link, format_timestamp, select_range
from aws import list_metrics, get_metric_data, create_cloudwatch_alarm
from timeseries import zero_pad, get_breaches, longest_breach

# Define constants
WEIGHTS = {'Namespace': 0.5, 'MetricName': 0.3, 'Dimensions': 0.3}
MAX_ITERATIONS = 100


def prompt_metric_search(metrics):
    """Prompts the user for a metric search and returns a selected metric."""
    click.echo('Enter a metric search eg "EC2 CPUUtilization XService"')
    while True:
        search = click.prompt('Search', type=str)
        click.echo('Select a metric from the list below')

        metrics = sorted(metrics, key=lambda metric: WEIGHTS['Namespace'] * fuzz.token_set_ratio(search, metric['Namespace']) +
                         WEIGHTS['MetricName'] * fuzz.token_set_ratio(search, metric['MetricName']) +
                         WEIGHTS['Dimensions'] * fuzz.token_set_ratio(search, json.dumps(metric['Dimensions'])), reverse=True)

        for i, metric in enumerate(metrics[:5]):
            click.echo(
                f"{i + 1}: {metric['Namespace']} {metric['MetricName']} {json.dumps({dimension['Name']: dimension['Value'] for dimension in metric['Dimensions']})}")

        click.echo("6: Search again")

        selected_metric = click.prompt('Please enter a number to select a metric', type=int)
        click.echo()

        if selected_metric == 6:
            continue

        if selected_metric < 1 or selected_metric > 5:
            click.echo('Invalid selection.')
            continue

        return metrics[selected_metric - 1]


def retrieve_and_pad_data(metric, period, statistic, aws_profile, region):
    """Retrieves and pads metric data."""
    start, end = select_range()

    click.echo(f"Retrieving data from {format_timestamp(start)} to {format_timestamp(end)}.")

    data = get_metric_data(start, end, metric['MetricName'], metric['Namespace'],
                           metric['Dimensions'], period, statistic, aws_profile, region)
    click.echo(f"Retrieved {len(data)} data points.")

    if len(data) == 0:
        click.echo("No data found.")
        return []

    data = zero_pad(data, period, start, end)
    click.echo(f"Padded data to {len(data)} data points.")
    return data, start, end


def calculate_threshold_and_breaches(data, alarm_type, min_duration, max_alerts):
    """Calculates threshold and breaches for the given data."""
    # Initial values
    threshold = 0
    breaches = get_breaches(data, threshold, alarm_type,
                            min_duration, int(min_duration/2))

    values = [value for timestamp, value in data]
    sum_values = sum(values)
    std_dev = sum([abs(value - sum_values / len(values))
                  for value in values]) / len(values)

    # Threshold search when breaches are too many or too long
    if len(breaches) > max_alerts or longest_breach(breaches) > timedelta(days=2):
        click.echo('Starting binary search for threshold.')

        # mean +/- 5 standard deviations depending on the alarm type
        if alarm_type == 'gt':
            threshold = math.ceil(sum_values / len(values) + 5 * std_dev)
        elif alarm_type == 'lt':
            threshold = math.ceil(sum_values / len(values) - 5 * std_dev)

        min_threshold = min(values)
        max_threshold = max(values) * 2

        for i in range(MAX_ITERATIONS):
            click.echo(
                f"Iteration {i + 1}. Evaluating threshold of {threshold}.")
            threshold = math.ceil((min_threshold + max_threshold) / 2)
            breaches = get_breaches(
                data, threshold, alarm_type, min_duration, int(min_duration/2))

            if len(breaches) > max_alerts:
                min_threshold = threshold
            else:
                if longest_breach(breaches) < timedelta(days=2):
                    break
                else:
                    min_threshold = threshold
                    max_threshold = max_threshold * 2

    return threshold, breaches


def output_rating_and_adjustment(metric, data, alarm_type, threshold, min_duration, breaches, start, region, statistic, period):
    """Handles output rating and adjustment based on user feedback."""
    while True:
        if threshold > 1:
            threshold = math.ceil(threshold)

        click.echo(f"X {alarm_type} {threshold} for {int(min_duration/2)} in {min_duration} datapoints would have resulted in {len(breaches)} breaches since {format_timestamp(start)}.")

        table_data = [['Start', 'End', 'Duration', 'Link']]

        for breach in breaches:
            duration = breach['end'] - breach['start']
            link = create_cloudwatch_link(
                metric['Namespace'], metric['MetricName'], breach['start'],
                breach['end'], metric['Dimensions'], threshold, region, statistic, period
            )
            table_data.append([format_timestamp(breach['start']),
                              format_timestamp(breach['end']), duration, link])

        if len(table_data) > 1:
            table = AsciiTable(table_data)
            click.echo(table.table)
            click.echo()

        click.echo("Rate the output")
        click.echo("1: Too many alerts")
        click.echo("2: Too few alerts")

        if len(breaches) > 0:
            click.echo("3: Incident(s) too short")
            click.echo("4: Incident(s) alerted too late")

        click.echo("5: Just right")

        rating = click.prompt(
            'Please enter a number to rate the output', type=int)
        click.echo()

        if rating == 1:
            click.echo("Increasing threshold by 10%")
            threshold = math.ceil(threshold * 1.1)
            breaches = get_breaches(
                data, threshold, alarm_type, min_duration, int(min_duration/2))
        elif rating == 2:
            click.echo("Decreasing threshold")
            if threshold < 10:
                threshold = threshold - 1
            else:
                threshold = math.ceil(threshold * 0.9)
            breaches = get_breaches(
                data, threshold, alarm_type, min_duration, int(min_duration/2))
        elif rating == 3:
            click.echo("Increasing minimum duration by 1 minute")
            min_duration += 1
            breaches = get_breaches(
                data, threshold, alarm_type, min_duration, int(min_duration/2))
        elif rating == 4:
            if min_duration == 1:
                click.echo("Minimum duration cannot be decreased further")
                continue
            click.echo("Decreasing minimum duration by 1 minute")
            min_duration -= 1
            breaches = get_breaches(
                data, threshold, alarm_type, min_duration, int(min_duration/2))
        elif rating == 5:
            break

    return threshold, min_duration


def ask_to_create_alarm(metric, threshold, alarm_type, aws_profile, region, statistic, period, min_duration):
    """Asks the user if they want to create a CloudWatch alarm and creates it if they do."""
    if click.confirm('Create/Update an alarm for this metric?', default=True):
        create_cloudwatch_alarm(
            metric['MetricName'], metric['Namespace'], metric['Dimensions'], threshold, alarm_type,
            aws_profile=aws_profile, region=region, statistic=statistic, period=period, min_duration=min_duration
        )


def run(alarm_type, aws_profile=None, period=5, statistic='Sum', region='us-east-1', min_duration=5, max_alerts=5):
    """Select threshold for CloudWatch metrics."""
    try:
        metrics = list_metrics(aws_profile, region)
    except Exception as e:
        click.echo(f"Failed to list metrics: {e}")
        return 1  # Non-zero status code to indicate an error

    try:
        metric = prompt_metric_search(metrics)
    except Exception as e:
        click.echo(f"Failed to prompt for metric search: {e}")
        return 1

    try:
        data, start, end = retrieve_and_pad_data(
            metric, period, statistic, aws_profile, region)
    except Exception as e:
        click.echo(f"Failed to retrieve and pad data: {e}")
        return 1

    if len(data) == 0:
        return 0

    try:
        threshold, breaches = calculate_threshold_and_breaches(
            data, alarm_type, min_duration, max_alerts)
    except Exception as e:
        click.echo(f"Failed to calculate threshold and breaches: {e}")
        return 1

    try:
        threshold, min_duration = output_rating_and_adjustment(
            metric, data, alarm_type, threshold, min_duration, breaches, start, region, statistic, period
        )
    except Exception as e:
        click.echo(f"Failed to adjust output based on rating: {e}")
        return 1

    try:
        ask_to_create_alarm(metric, threshold, alarm_type,
                            aws_profile, region, statistic, period, min_duration)
    except Exception as e:
        click.echo(f"Failed to create alarm: {e}")
        return 1

    return 0
