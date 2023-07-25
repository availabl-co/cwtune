"""Console script for CloudTune."""
import sys
import click
import cwtune

@click.command()
@click.option('--alarm-type', prompt='Alarm Type', type=click.Choice(['gt', 'lt']), help='The type of alarm, greater than (gt) or less than (lt).')
@click.option('--period', prompt='Period (Mins)', default="5", type=click.Choice(["1", "5", "60"]), help='The period of the CloudWatch metric in minutes.')
@click.option('--statistic', prompt='Statistic', default='Sum', type=click.Choice(['Sum', 'Average', 'Min', 'Max']), help='The statistic of the CloudWatch metric.')
@click.option('--region', prompt='Region', help='The region of the CloudWatch metric.')
@click.option('--aws-profile', prompt='AWS CLI Profile', required=False, help='(Optional) The profile configured in AWS CLI to use for making API calls.')
def main(alarm_type, aws_profile=None, period=5, statistic='Sum', region='us-east-1'):
    """Console script for CloudTune. This script automates the process of threshold selection for CloudWatch metrics."""
    
    # This message will be replaced by your actual logic
    cwtune.run(alarm_type, aws_profile, int(period), statistic=statistic, region=region)

    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
