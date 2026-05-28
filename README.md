# AI-Powered IT Ticket Triager

A serverless backend that uses Claude to read incoming IT support tickets, categorize and prioritize them, draft a response, and post the result to a team Discord channel.

I built this to bridge my IT support background with cloud engineering and AI work. It's the kind of automation a small IT team could actually use to cut triage time on tier-1 tickets.

## What it does

A user submits a ticket (through a simple HTML form or any HTTP client). The request goes to an AWS API Gateway endpoint, which triggers a Lambda function. The function sends the ticket to Claude with a prompt asking for structured JSON back: a category, a priority level, a one-sentence summary, and a draft response. Lambda parses the response and posts a formatted embed to Discord, color-coded by priority so the team can scan and prioritize at a glance.

The whole thing runs in a few seconds and costs almost nothing.

## Stack

- AWS Lambda (Python 3.12) for the backend logic
- AWS API Gateway for the public HTTPS endpoint
- Claude API (claude-opus-4-5) for the triage itself, called via raw HTTP with urllib3 — no SDK
- Discord webhook for team notifications
- A static HTML/JS page for the demo frontend

## Architecture

```
Submitter (form or API client)
        |
        v
AWS API Gateway
        |
        v
AWS Lambda (Python)
        |
        v
Claude API  ----> structured JSON triage
        |
        v
Discord webhook
```

## Repo contents

```
ai-it-ticket-triager/
  lambda_function.py        # Lambda backend
  ticket-submit.html        # HTML frontend
  screenshots/              # Working proof
    01-lambda-test-success.png
    02-discord-notification.png
    03-aws-architecture.png
  README.md
```

## How to run it yourself

You'll need an AWS account, an Anthropic API key from console.anthropic.com, and a Discord server with a webhook set up.

1. Create a new Lambda function. Python 3.12 runtime. Paste in `lambda_function.py`. Bump the timeout to 30 seconds since the Claude API call takes a few seconds.

2. Set two environment variables on the function:
   - `ANTHROPIC_API_KEY` — your Anthropic key
   - `DISCORD_WEBHOOK_URL` — your Discord webhook URL

3. Add an API Gateway trigger. HTTP API, open authorization (fine for a demo, but you'd want auth for anything real). Enable CORS with `*` origin, `POST,OPTIONS` methods, and `content-type` in the allowed headers.

4. Open `ticket-submit.html`, swap in your own API Gateway URL where mine is, and serve it through a local HTTP server (Python's `http.server` works) rather than opening it as a file — browsers block the file:// origin on CORS preflight.

## Decisions worth explaining

**No Anthropic SDK.** Lambda doesn't ship with the `anthropic` Python library, and I was working with a fresh AWS account that hadn't been verified for CloudShell yet (which would've made building a Lambda Layer easy). Instead of waiting, I called the Claude API directly with `urllib3`, which is already in the Lambda runtime. It works the same, has fewer moving parts, and makes the project easier for someone else to deploy.

**API Gateway instead of SES email ingestion.** I originally planned to pull tickets from a real email inbox using Amazon SES. I switched to API Gateway for two reasons: SES email receiving needs a verified domain and AWS sandbox approval, neither of which I wanted to chase down at 11pm; and an API endpoint is actually more useful, because it can be triggered by anything that can POST JSON — a form, Zapier, an internal tool, another service. Email ingestion is a clean v2 add later.

**Structured JSON output from Claude.** The prompt tells Claude to respond with only a JSON object in a specific schema. That makes parsing reliable and avoids any regex extraction.

**Color-coded Discord embeds.** Priority maps to embed color (green, yellow, orange, red). Lets the team triage visually without reading every message.

## Known issue

The HTML form throws a CORS preflight error when opened directly as a local file (file:// origin). Running it through a local HTTP server works. The cleanest fix is to host the frontend on S3 with CloudFront in front of it — listed in future improvements below.

## Future improvements

- Email ingestion via AWS SES so the tool can read a real support inbox
- DynamoDB layer to log every ticket for historical reporting
- A simple dashboard showing ticket volume by category and priority
- Slack support alongside Discord
- Auto-response for low-priority known issues, so Claude's draft goes straight to the user without a human in the loop
- Frontend hosted on S3 + CloudFront

## What I learned building this

The biggest thing was getting comfortable with event-driven serverless work — how Lambda, API Gateway, IAM, and environment variables actually fit together when something has to talk to something else. I also got real practice debugging in a cloud environment: timeouts, syntax errors that only show up when the function tries to load, CORS preflight failures, deploy stages that need to be promoted. Most of the project was solving those small problems one at a time, which is what the work actually looks like.

The other thing was prompt engineering for reliable output. Asking Claude for JSON in a strict schema and getting it back the same way every time is its own small skill — important if you want an LLM to be a real component in a pipeline rather than a chatbot.

## Author

Vadim Biteau
github.com/vbiteau
