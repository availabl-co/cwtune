import requests
from datetime import datetime, timedelta, timezone


def shorten_url(url):
    """Shorten the URL using the 'tinyurl.com' service."""
    try:
        url = requests.utils.quote(url, safe='')
        response = requests.get(
            'http://tinyurl.com/api-create.php?url={}'.format(url))
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error while shortening the URL: {e}")
        return url


def create_cloudwatch_link(namespace: str, metric_name: str, start: datetime, end: datetime, dimensions: list, threshold: float, region: str, statistic: str, period: int, shorten=True) -> str:
    """Create a link to the CloudWatch graph for the given metric."""
    base_url = f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#metricsV2?"

    encoded_namespace = namespace.replace('/', '*2f')

    encoded_dimensions_list = [
        f"~'{d['Name']}~'{d['Value']}" for d in dimensions]
    encoded_dimensions = ''.join(encoded_dimensions_list)

    duration = end - start
    padded_start = start - max([duration, timedelta(minutes=30)])
    padded_end = end + max([duration, timedelta(minutes=30)])

    formatted_padded_start = padded_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    formatted_padded_end = padded_end.strftime("%Y-%m-%dT%H:%M:%SZ")

    formatted_start = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    formatted_end = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    graph_str = f"(view~'timeSeries~stacked~false~metrics~(~(~'{encoded_namespace}~'{metric_name}{encoded_dimensions}))~region~'{region}~start~'{formatted_padded_start}~end~'{formatted_padded_end}~annotations~(horizontal~(~(label~'Threshold~value~{threshold}))~vertical~(~(label~'Start~value~'{formatted_start})~(label~'End~value~'{formatted_end})))~stat~'{statistic}~period~{period * 60})"
    query_str = "*7b{}*2c{}*7d".format(encoded_namespace,
                                       '*2c'.join([f"'{d['Name']}'" for d in dimensions]))

    full_url = base_url + "graph=~" + graph_str + "&query=~'" + query_str

    if shorten:
        return shorten_url(full_url)
    else:
        return full_url


def format_timestamp(timestamp):
    """Format the timestamp."""
    return timestamp.strftime('%Y-%m-%d %H:%M:%S')


def select_range():
    """Select the range for the timestamp."""
    start = datetime.utcnow() - timedelta(days=14)
    end = datetime.utcnow()

    start = start - timedelta(seconds=start.second,
                              microseconds=start.microsecond)
    end = end - timedelta(seconds=end.second, microseconds=end.microsecond)

    start = start.replace(tzinfo=timezone.utc)
    end = end.replace(tzinfo=timezone.utc)
    return start, end
