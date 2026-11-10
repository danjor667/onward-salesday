# Decisions

Each decision, with its reason in business terms and what was rejected.

| # | Decision | Reason | Rejected alternative |
|---|---|---|---|
| 1 | Two servers minimum, one per Availability Zone | Two is the smallest number that survives the loss of a server or a whole zone without anyone acting | One server: half the cost, but any failure is an outage until a replacement boots |
| 2 | Six servers maximum | Three times the lean size, matching "order volume triples". Also a hard ceiling on the bill if something loops | No ceiling: a bug or an attack could run up unlimited cost |
| 3 | Scale on average CPU, target 50% | The CTO asked for capacity to follow server CPU. 50% leaves room to absorb a spike during the minutes a new server needs to start | 70 to 80%: cheaper, but servers are already struggling before help arrives. Scaling on request count: needs a known "requests per server" figure the client does not have yet |
| 4 | Target tracking policy | One number to explain and tune. AWS manages the alarms and both directions | Step scaling: more control, more to maintain and get wrong. Scheduled scaling: only works if sales days are known in advance; a good addition later |
| 5 | Scale in slowly (about 15 minutes of low CPU), scale out quickly | Removing servers too early during a lull in a sales day would cause the slow pages the client is trying to avoid | Aggressive scale in: saves cents, risks customer experience |
| 6 | `t3.micro`, Amazon Linux 2023 | Free Tier eligible in this account, enough for this application, and small servers make scaling steps fine-grained | Larger instances: fewer of them, so each failure removes a bigger share of capacity |
| 7 | CPU credits set to `unlimited` | These are burstable servers. With `standard`, a `t3` that runs out of credits is slowed to about 10% CPU, so the CPU metric stops rising exactly when demand is highest and scaling stalls | `standard`: never costs extra, but can hide the very signal scaling depends on. The extra charge for `unlimited` is small and only applies while a server stays busy |
| 8 | Regional NAT Gateway for outbound access | Servers can download packages and updates but nothing can connect in. One gateway covers every zone and manages itself, so there is less to configure wrongly | One zonal NAT gateway: cheaper, but outbound access for both zones is lost if its zone fails. Public IPs on servers: no NAT cost, but breaks the security requirement |
| 9 | No SSH, no key pair, no port 22. Access through Systems Manager Session Manager | Security asked that nobody opens admin ports. Sessions are tied to a named AWS identity and recorded | Bastion host with SSH: another server to patch, pay for and protect, plus keys to manage |
| 10 | The load test is a Systems Manager command, not a button on the page | A public "make the servers busy" button is something any visitor could press to run up cost or slow the service. The command needs AWS credentials and is logged | A button protected by a password sent over plain HTTP: the password would be readable in transit |
| 11 | Each server installs the application itself at launch, from this repository | A new server is ready without anyone touching it, and the same script runs every time | A pre-built machine image: faster to start (worth doing when start time matters), but needs an image pipeline. Manual install: does not scale |
| 12 | Health check by the load balancer, not only "is the machine running" | A server whose application has crashed is replaced, even though the machine is still on | EC2 status checks only: a broken application would keep receiving customers |
| 13 | Detailed (one minute) CPU monitoring | Scaling reacts in about three minutes instead of ten or more | Basic five minute monitoring: free, but a tripling of orders "within hours" can still outrun it |
| 14 | One template | The lab asks for one, and the stack is small enough to read top to bottom in numbered sections | Several stacks: clearer ownership at larger scale, more moving parts here |
| 15 | HTTP only on the load balancer | The lab provides no domain name, and a certificate needs one | See limits |
| 16 | Region: `eu-central-1` (to confirm) | It is the Region configured in the AWS CLI used to build this. **Confirm or change, and write the justification here**: the Client Profile asks for the Region to be chosen and justified | |

## Limits

- **No HTTPS.** Production needs a domain, an ACM certificate and a 443 listener.
- **Orders are stored in memory, per server.** Each server has its own list, so a refresh that lands on another server shows different orders, and a replaced server starts again with the sample orders. A real order system needs a shared database; storage is outside this lab.
- **New servers take a few minutes** to boot and install. A very sudden spike is absorbed by the headroom below the 50% target, not by new servers. A pre-built image or scheduled scaling before known sales days would shorten this.
- **The load test makes servers busy directly**; it does not send customer traffic. It proves the scaling behaviour, not how many orders per second a server handles.
- **The repository must be public** for servers to download it.
- **Application logs stay on each server** (`journalctl -u onward-orders`). Sending them to CloudWatch would let operations read them after a server is gone.
- **The GitSync role is broad.** It can create any `onward-*` IAM role. A permissions boundary would narrow it further.
