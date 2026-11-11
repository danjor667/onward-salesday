# Cost

Prices are approximate on-demand list prices for `eu-central-1` and differ
by Region. Free Tier allowances or credits, if the account has them, reduce
these figures.

**Official estimate (public link, no AWS account needed):**
[Onward Logistics - Lab 1 Sales Day (eu-central-1)](https://calculator.aws/#/estimate?id=e34730670194ab6ccce1bf92ca342f5bdccbf694)
on the AWS Pricing Calculator: **USD 121.57 per month**, saved on 11 November 2026.
The link expires after one year.

| Line in the public estimate | USD / month |
|---|---|
| Amazon EC2: 2 × `t3.micro` all month, 8 GB gp3 each, detailed monitoring | 23.24 |
| Amazon EC2: sale days, 4 extra `t3.micro` × 32 h (8 h × 4 sale days), 8 GB gp3 | 1.68 |
| Elastic Load Balancing: 1 Application Load Balancer, low traffic | 19.79 |
| Amazon VPC: 1 Regional NAT Gateway active in 2 zones, 10 GB processed | 76.44 |
| Amazon DynamoDB: on-demand, 120,000 writes, 300,000 reads, 1 GB | 0.42 |
| **Total** | **121.57** |

The public calculator has no field for `unlimited` CPU credits on sale days (about USD 2
more), which is why it is slightly below the console estimate below.

## AWS Pricing Calculator estimate

**Estimate:** `onward-dev-salesday-monthly` in the AWS console's Pricing Calculator
([Billing and Cost Management → Pricing Calculator → Workload estimates](https://us-east-1.console.aws.amazon.com/costmanagement/home#/pricing-calculator)),
priced by AWS at on-demand rates for `eu-central-1` on 11 November 2026. Anyone signed in
to this AWS account can open it; it expires on 11 December 2027.

**Total: USD 124.30 per month**, assuming four sale days a month.

| Group | Usage entered | USD / month |
|---|---|---|
| Quiet days: 2 servers | 2 × `t3.micro` × 730 h; 17.4 GB-month gp3 | 19.18 |
| Sale days: up to 4 extra servers | 4 × 8 h × 4 sale days = 128 h; 40 vCPU-hours of `unlimited` CPU credits | 3.54 |
| Network: Regional NAT Gateway | 2 zones × 730 h; 10 GB processed | 76.44 |
| Network: Application Load Balancer | 730 h; 100 LCU-hours | 20.51 |
| Monitoring: 1-minute EC2 metrics | 15 detailed-monitoring metrics | 4.50 |
| Orders: DynamoDB on-demand | ~30,000 orders: 120,000 writes, 300,000 reads | 0.14 |
| **Total** | | **124.30** |

What this shows the Finance Lead: the sale-day capacity adds about USD 3.50 a month, while
the always-on network pieces (NAT gateway and load balancer) are about 78% of the bill.


## Quiet day and peak day

Assumptions: a quiet day runs the two minimum servers all day. A peak day
runs two servers for 16 hours and six servers for 8 hours.

| Item | Approx. unit price | Quiet day | Peak day |
|---|---|---|---|
| Servers (`t3.micro`) | $0.012 per hour each | 2 × 24 h = **$0.58** | (2 × 16 h) + (6 × 8 h) = **$0.96** |
| Extra CPU credits (`unlimited`) | $0.05 per vCPU-hour above baseline | $0 | up to about **$0.50** if servers stay busy for hours |
| Detailed monitoring | about $2.10 per server per month | $0.14 | $0.23 |
| Load balancer | about $0.027 per hour, plus usage | **$0.65** | about **$0.75** (more requests) |
| Regional NAT Gateway | about $0.052 per hour per zone in use, plus about $0.052 per GB | 2 zones × 24 h = **$2.50** | **$2.50** plus a little data |
| Disks (8 GB gp3 per server) | about $0.095 per GB-month | $0.05 | $0.09 |
| DynamoDB orders table (on-demand) | about $1.25 per million writes, $0.25 per million reads | under $0.01 | a few cents, even at three times the orders |
| **Total** | | **about $3.90** | **about $5.00** |

Per month that is roughly **$120** if every day were quiet.

## What this shows

- **A peak day costs about a dollar more than a quiet day.** Tripling the servers for eight hours adds cents, because servers are the cheap part.
- **Running peak capacity all month would cost about $1.15 more per day** in servers alone (six servers instead of two), for capacity that sits idle most of the time. At this size the saving is small; it grows in proportion as the system does, and the larger benefit is not having to guess the peak or resize by hand.
- **The fixed parts dominate.** The NAT gateway and the load balancer cost about $3.15 a day whether or not anyone places an order. The NAT gateway alone is about two thirds of the quiet day bill.

## Choices that affect cost

| Choice | Cost effect | Why it was kept |
|---|---|---|
| Regional NAT Gateway across two zones | The largest single item | Required by the lab, and it keeps outbound access working if a zone fails. A single zonal gateway would roughly halve it at the price of that resilience. **Confirm how the regional gateway is billed** on the [VPC pricing page](https://aws.amazon.com/vpc/pricing/) |
| Two servers minimum instead of one | +$0.29 per day | Survives a server or zone failure with no action |
| `unlimited` CPU credits | Up to cents per busy server-hour | Without it, a busy server is slowed down and scaling may not trigger |
| Detailed monitoring | +$0.07 per server per day | Scaling reacts in minutes rather than ten or more |
| Maximum of six servers | Caps server cost at about $1.75 per day | A ceiling on the bill |

## Building the estimate

In the [AWS Pricing Calculator](https://calculator.aws/#/), choose *Create
estimate*, set the Region, and add these services. Make two groups, "Quiet
day" and "Peak day", so the Finance Lead sees both side by side.

| Service to add | What to enter | Price list |
|---|---|---|
| Amazon EC2 | `t3.micro`, Linux, on-demand. Quiet: 2 instances. Peak: 2 instances always on plus 4 instances for 8 hours a day. 8 GB gp3 storage each. Detailed monitoring on | [EC2 on-demand pricing](https://aws.amazon.com/ec2/pricing/on-demand/) |
| Elastic Load Balancing | 1 Application Load Balancer, with an estimate of requests and data per hour | [Elastic Load Balancing pricing](https://aws.amazon.com/elasticloadbalancing/pricing/) |
| Amazon VPC, NAT Gateway | 1 regional NAT gateway, 2 Availability Zones, a few GB of data per month | [VPC pricing](https://aws.amazon.com/vpc/pricing/) |
| Amazon CloudWatch | Detailed monitoring metrics for the instances | [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/) |
| Amazon DynamoDB | On-demand capacity, with the number of orders per day (each order is a handful of writes and reads). Quiet: your normal volume. Peak: three times that | [DynamoDB pricing](https://aws.amazon.com/dynamodb/pricing/on-demand/) |

Then choose *Share* and paste the public link at the top of this page.
Extra CPU credits for `unlimited` mode are explained under "Unlimited mode"
on the [EC2 burstable instances page](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances-unlimited-mode.html).

## Keeping spend visible

- **Budget alert.** The Client Profile asks for budget alerts to stay active.
  [AWS Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/)
  emails you when actual or forecast spend passes a limit; budgets that only
  send alerts are free. Set the monthly limit a little above the
  estimate (for example $130) so a runaway scale-out is noticed.
- **Tags.** Every resource carries `Project`, `Owner` and `Environment`.
  Activate them as cost allocation tags in Billing, then filter
  [Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/)
  by `Project = onward` to compare the real bill with the estimate.
- **Idle environments.** Delete the stack when the environment is not
  needed: it can be rebuilt from the repository in a few minutes.
