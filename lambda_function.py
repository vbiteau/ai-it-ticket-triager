import json
import os
import urllib3

http = urllib3.PoolManager()

def call_claude(email_content):
    """Call Claude API directly via HTTP (no SDK needed)."""
    
    prompt = f"""You are an IT support triage assistant. Analyze this support ticket and respond with ONLY a JSON object in this exact format (no markdown, no extra text):

{{
  "category": "password_reset | hardware | software | network | account_access | other",
  "priority": "low | medium | high | urgent",
  "summary": "one sentence summary",
  "suggested_response": "draft response to the user"
}}

Ticket:
{email_content}"""

    response = http.request(
        'POST',
        'https://api.anthropic.com/v1/messages',
        headers={
            'x-api-key': os.environ['ANTHROPIC_API_KEY'],
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        },
        body=json.dumps({
            'model': 'claude-opus-4-5',
            'max_tokens': 1024,
            'messages': [{'role': 'user', 'content': prompt}]
        })
    )
    
    result = json.loads(response.data.decode('utf-8'))
    claude_text = result['content'][0]['text']
    return json.loads(claude_text)


def send_to_discord(triage, submitter=None):
    """Post the triage results to Discord."""
    
    colors = {'low': 3066993, 'medium': 16776960, 'high': 15158332, 'urgent': 10038562}
    
    fields = [
        {"name": "Priority", "value": triage['priority'].upper(), "inline": True},
        {"name": "Category", "value": triage['category'].replace('_', ' ').title(), "inline": True},
        {"name": "Suggested Response", "value": triage['suggested_response'][:1024]}
    ]
    
    if submitter:
        fields.insert(0, {"name": "From", "value": submitter, "inline": True})
    
    discord_message = {
        "embeds": [{
            "title": f"🎫 New Ticket: {triage['summary'][:240]}",
            "color": colors.get(triage['priority'], 8421504),
            "fields": fields
        }]
    }
    
    http.request(
        'POST',
        os.environ['DISCORD_WEBHOOK_URL'],
        body=json.dumps(discord_message),
        headers={'Content-Type': 'application/json'}
    )


def lambda_handler(event, context):
    try:
        # Check if this is an API Gateway request (has a 'body' key)
        if 'body' in event and event['body']:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            ticket_text = body.get('ticket', body.get('email_body', ''))
            submitter = body.get('submitter', body.get('from', None))
        else:
            # Direct Lambda test event
            ticket_text = event.get('ticket', event.get('email_body', 'No ticket content provided'))
            submitter = event.get('submitter', None)
        
        if not ticket_text:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'No ticket content provided'})
            }
        
        triage = call_claude(ticket_text)
        send_to_discord(triage, submitter)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'content-type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'success': True,
                'triage': triage
            })
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }