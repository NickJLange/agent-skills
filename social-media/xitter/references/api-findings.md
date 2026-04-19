# X API Practical Findings

## Authentication Confusion Guide

X Developer Portal uses overlapping terminology. Quick disambiguation:

| Portal Label | Env Var | Purpose |
|---|---|---|
| API Key | X_API_KEY | Consumer key — identifies your app |
| API Secret | X_API_SECRET | Consumer secret — signs OAuth1 requests |
| Bearer Token | X_BEARER_TOKEN | App-only read auth (no user context) |
| Access Token | X_ACCESS_TOKEN | OAuth1 user token — acts as you |
| Access Token Secret | X_ACCESS_TOKEN_SECRET | OAuth1 user secret — signs requests as you |
| Client ID (OAuth 2.0) | X_OAUTH2_CLIENT | Different system — NOT the same as API Key |
| Client Secret (OAuth 2.0) | X_OAUTH2_CLIENT_SECRET | Different system — NOT the same as API Secret |

Common mistake: Copying API Key/Secret into the Access Token/Secret fields.
They must be DIFFERENT values. Access tokens are generated separately under
"Keys and tokens" > "Access Token and Secret" > Generate.

Another common mistake: Copying OAuth 2.0 client credentials into OAuth 1.0a
fields. They are incompatible systems.

## What Works With Bearer Token Only (No OAuth1)

- User lookup (user get)
- Tweet search (tweet search)
- Timeline reading (user timeline)
- Follower/following lists
- Lists: GET /2/users/:id/owned_lists
- List tweets: GET /2/lists/:id/tweets

## What Requires OAuth1 User Access Tokens

- Bookmarks (get/post/delete)
- Mentions
- Posting tweets
- Liking tweets
- Retweeting
- Any operation that "acts as you"

## Lists API (Direct Calls via Python urllib)

x-cli does not have lists support. Use direct API calls via Python urllib
(curl may not be available in this environment):

```python
import urllib.request, json
bearer = 'YOUR_BEARER_TOKEN'

# Get user's lists by user ID
req = urllib.request.Request(
    'https://api.x.com/2/users/USER_ID/owned_lists?max_results=25',
    headers={'Authorization': f'Bearer {bearer}'}
)
data = json.loads(urllib.request.urlopen(req).read())

# Get tweets from a list
req = urllib.request.Request(
    'https://api.x.com/2/lists/LIST_ID/tweets?max_results=15',
    headers={'Authorization': f'Bearer {bearer}'}
)
data = json.loads(urllib.request.urlopen(req).read())
```

## xurl — Official X CLI Alternative

If OAuth1 access tokens are unavailable, xurl supports OAuth 2.0 PKCE flow.
GitHub: https://github.com/xdevplatform/xurl

Install: Download binary from GitHub releases using Python urllib.
Register: xurl auth apps add NAME --client-id ID --client-secret SECRET
Auth: xurl auth oauth2 (opens browser for PKCE flow)
Requires: redirect URI = http://localhost:8080/callback in X Developer Portal.

## Multi-Account Structure

```
~/.config/x-cli/
├── .env -> accounts/<active>.env
├── accounts/
│   ├── nickjlange.env
│   └── 5l_labs.env
└── switch-account.sh
```
