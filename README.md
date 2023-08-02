
# cwtune

## Description

`cwtune` is an open-source tool developed by [availabl.ai](https://availabl.ai). It addresses the issue of noisy CloudWatch alarms by providing a data-driven approach for selecting better thresholds. 

Thresholds for these monitors are usually selected by trial and error, which can lead to unnecessary noise. `cwtune` uses historical data to backtest and suggest optimized thresholds, ensuring your alarms are tuned to the right level. This reduces unnecessary noise and increases the value of your alerts.

## Requirements
- [aws cli](https://aws.amazon.com/cli/)
- python 3.6+

## Installation

You can install `cwtune` via pip:

```bash
pip install cwtune
```

## Usage

After installation, you can run `cwtune` from the command line:

```bash
cwtune
```

The tool will then guide you interactively through the process of configuring your CloudWatch alarms.

Alternatively, you can provide command-line arguments to configure the alarms:

```bash
cwtune --alarm-type [gt|lt] --period [1|5|60] --statistic [Sum|Average|Min|Max] --region [AWS region] --aws-profile [AWS CLI profile]
```

Here's what each argument does:

- `--alarm-type`: The type of alarm, either greater than (`gt`) or less than (`lt`).
- `--period`: The period of the CloudWatch metric in minutes. Can be `1`, `5`, or `60`.
- `--statistic`: The statistic of the CloudWatch metric. Can be `Sum`, `Average`, `Min`, `Max`, `SampleCount`, `p50`, `p95` or `p99`.
- `--region`: The region of the CloudWatch metric. Can be any valid AWS region.
- `--aws-profile`: (Optional) The profile configured in AWS CLI to use for making API calls. Defaults to `default`.

For example, to configure a greater than alarm with a 1-minute period, using the `Sum` statistic, in the `us-west-1` region, and using the default AWS CLI profile, you would run:

```bash
cwtune --alarm-type gt --period 1 --statistic Sum --region us-west-1 --aws-profile default
```

## Example Plot
<img width="1544" alt="Screen Shot 2023-08-02 at 15 48 45 p m" src="https://github.com/availabl-co/cwtune/assets/89125058/1dd56b83-36c4-46d2-a40e-f29cfb657fdb">

## Contributing

We welcome contributions from the community! If you would like to contribute, please follow these steps:

1. Fork the repository on GitHub.
2. Make your changes in a new branch.
3. Test your changes to ensure they do not introduce new bugs.
4. Submit a pull request for review.

## License

`cwtune` is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
