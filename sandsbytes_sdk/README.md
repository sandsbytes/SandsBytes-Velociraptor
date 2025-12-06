# SandsBytes SDK

A Python SDK for interacting with the SandsBytes cybersecurity platform. This SDK provides easy-to-use methods for managing cases, users, evidences, IOCs, and other security-related data through the SandsBytes API.

## Features

- **Case Management**: Create, update, and manage cybersecurity cases
- **User & Role Management**: Handle user accounts and role assignments
- **Evidence Collection**: Upload and manage case evidence
- **IOC Management**: Track and manage Indicators of Compromise
- **Report Generation**: Create and download investigation reports
- **File Management**: Upload, download, and organize case files
- **Authentication**: Secure API authentication with automatic token management

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd SandsBytes-SDK
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

```python
from http_client import HTTPClient

# Initialize the SandsBytes client
client = HTTPClient(
    base_url="https://your-sandsbytes-server.com/api",
    config_file="config.json",
    ignore_ssl=True  # Set to False for production with valid SSL
)

# Authenticate with your SandsBytes credentials
if client.authenticate("your_username", "your_password"):
    print("Successfully connected to SandsBytes!")
    
    # Create a new security case
    case_data = {
        "status": "OPEN",
        "description": "Malware investigation case",
        "name": "Suspicious Email Analysis",
        "severity": "HIGH",
        "classification": "malware infection",
        "source": "Email Security Gateway"
    }
    
    response = client.cases.create(data=case_data)
    print(f"Case created with ID: {response.get('id')}")
    
    # List all open cases
    open_cases = client.cases.list()
    print(f"Found {len(open_cases)} cases")
    
else:
    print("Failed to authenticate with SandsBytes")
```

## What You Can Do with SandsBytes SDK

The SDK provides access to all major SandsBytes platform features:

- **Cases**: Create and manage cybersecurity investigation cases
- **Users & Roles**: Manage user accounts and assign roles/permissions
- **Evidence**: Upload, organize, and track case evidence files
- **IOCs**: Manage Indicators of Compromise (IPs, domains, hashes, etc.)
- **Findings**: Document investigation findings and analysis
- **Reports**: Generate and download investigation reports
- **Tasks**: Create and track investigation tasks
- **Timelines**: Build chronological case timelines
- **Remediations**: Document and track remediation actions
- **Templates**: Use and manage report templates
- **Feeds**: Integrate with threat intelligence feeds
- **Dashboards**: Create custom security dashboards
- **Others**: Any other feature can implemented in the SandsBytes API


## Discovering Available API Methods

The SandsBytes SDK automatically generates client methods based on the structure defined in your `config.json` file. This allows you to call any API endpoint with:

```
client.<category>.<method>(...)
```

Where:

- `<category>` is the top-level key in `config.json` (e.g., `cases`, `users`, `feeds`)
- `<method>` is the name of a sub-operation for that category (e.g., `create`, `list`, `delete`)

**How to Find Available Methods:**

1. **Open `config.json`**

   Locate your `config.json` file in the SandsBytes-SDK directory. You will see a structure like:

   ```json
   {
     "cases": {
       "list": { "path": "/cases", "method": "GET" },
       "create": { "path": "/cases/create", "method": "PUT" },
       "delete": { "path": "/cases/delete/{case_id}", "method": "DELETE" }
     },
     "users": {
       "list": { "path": "/users", "method": "GET" },
       "create": { "path": "/users/create", "method": "PUT" }
     }
     // ...
   }
   ```

2. **Determine the Methods:**

   - Each category (e.g., `cases`, `users`, `feeds`) becomes an attribute on your client.
   - Each method under that category (e.g., `list`, `create`, `delete`) becomes a callable sub-attribute.

   For example, to list all cases or users:

   ```python
   cases = client.cases.list()
   users = client.users.list()
   ```

   To create a new case:

   ```python
   case = client.cases.create(data={...})
   ```

3. **Programmatic Discovery (Advanced):**

   If you want to list all available categories and methods in code:

   ```python
   print(client.config.keys())  # List all categories
   print(client.config['cases'].keys())  # List all methods under 'cases'
   ```

**Example Mapping from config.json:**

```json
{
  "feeds": {
    "list": {
      "path": "/feeds",
      "method": "GET"
    },
    "add": {
      "path": "/feeds/add",
      "method": "POST"
    }
  }
}
```

Usage:

```python
client.feeds.list()
client.feeds.add(data={...})
```

> **Tip:** Whenever new endpoints are added to `config.json`, they are instantly available as new methods in the dynamically generated client object.




## Complete Example

Here's a complete example showing how to use the SandsBytes SDK for a typical cybersecurity investigation:

```python
from http_client import HTTPClient
import json

# Initialize client
client = HTTPClient(
    base_url="https://<host-ip>/api",
    config_file="config.json",
    ignore_ssl=True
)

# Authenticate
if not client.authenticate("username", "password"):
    print("Authentication failed!")
    exit(1)

# Create a new investigation case
case_data = {
    "status": "OPEN",
    "description": "Investigation of suspicious email campaign",
    "name": "Phishing Campaign Analysis",
    "severity": "HIGH",
    "classification": "phishing",
    "source": "Email Security Alert"
}
case = client.cases.create(data=case_data)
case_id = case.get('id')
print(f"Created case: {case_id}")

# Add requirements
requirements = [
    {"requirement": "Collect all suspicious emails", "status": "New", "request_date" : "2025-10-14 22:18:46", "responsible": "SOC Team"},
    {"requirement": "List all affected recipients", "status": "New", "request_date" : "2025-10-14 22:18:46", "responsible": "SOC Team"},
    {"requirement": "Obtain email headers and attachments", "status": "New", "request_date" : "2025-10-14 22:18:46", "responsible": "SOC Team"}
]

for req in requirements:
    client.requirements.create(case_id=case_id, data=req)
print(f"Requirements added")

# Create investigation tasks
tasks = [
    {"title": "Inspect email attachments", "status": "To Do", "users": 2, "due_at": "2025-10-16", "description": "Analyze all attachments for malware or suspicious content."},
    {"title": "Extract sender domains", "status": "To Do", "users": 1, "due_at": "2025-10-16", "description": "List and verify all sender domains from suspicious emails."},
    {"title": "Check recipient mailbox activity", "status": "To Do", "users": 1, "due_at": "2025-10-17", "description": "Review mailbox logs for signs of compromise in recipients."}
]

for task in tasks:
    client.tasks.create(case_id=case_id, data=task)

# Document findings
finding_data = {
    "title": "Phishing Campaign Analysis",
    "finding": "Confirmed phishing campaign targeting banking customers",
    "source": "DESKTOP",
    "severity": "Critical",
    "mitres": '[{"tactic_id":"TA0005","technique_id":"T1622","subtechnique_id":null}]'
}
client.findings.create(case_id=case_id, data=finding_data)

# 
# Get template with name "Case Report Template (DOCX)"
template_query = {
    "query" : '[{"field":"name","op":"==","type":"text","value":"Case Report Template (DOCX)"},{"field":"_string","op":"ilike","value":""}]'
}
template = client.templates.list(query=template_query)

template_id = template.get("templates", [])[0].get('id')

# Generate report using the retrieved template_id
report_data = {
    "template_id": template_id,
    "name": 'Incident Response Report {{ CASE.0.name }} - {{ REPORT.created_at[:10] }}',
}
report = client.reports.create(case_id=case_id, data=report_data)

# Update case status
client.cases.edit(case_id=case_id, data={"status": "CLOSED"})

print("Investigation completed successfully!")

```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions, please contact the SandsBytes team or create an issue in the repository.
