## Powerful REST API *microservice* on Tornado

### Main goal
Sometimes (actually constantly) we need to deploy microservices like messenger bots (telegram, facebook), small backends, webhooks and other. 

### Features
- tornado with improved basic handler for easy create REST endpoints
- async non-blocking highly durable and scalable
- handlers versioning (e.g. GET /**v2**/cat?color=blue)
- request validation, answer containerization
- poor documented, sorry :(

### Under the hood
- tornado 5

All features below are optional
- peewee / peewee_async as ORM
  - User and session models
  - oauth support
- simple redis caching
- sentry integration + telegram reports
- prometheus monitoring

### Testing
1. PYTHONPATH=./microservice python test.py
1. curl localhost:8001/v1/test | json_pp
1. inspect test.py and enjoy


### Getting started
coming soon...
