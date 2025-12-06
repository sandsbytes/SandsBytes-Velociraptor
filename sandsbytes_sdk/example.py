from http_client import HTTPClient
import json

def main():
    client = HTTPClient(
        base_url        = "https://192.168.237.134/api",
        auth_path       = "/auth/login",
        config_file     = "config.json",
        ignore_ssl      = True
    )
    client.authenticate("admin", "Password@123")

    print(f"Authenticated: {client.is_authenticated()}\n")

    case_data = {
        "status"        : "CLOSED",
        "description"   : "Test case",
        "name"          : "Test API",
        "severity"      : "LOW",
        "classification": "malware infection",
        "source"        : "DESKTOP-XXXXX"
    }

    client.cases.create(data=case_data)


    print(client.cases.list(params={"query": json.dumps([{"field": "id", "op": "==", "value": 10}])}))


if __name__ == "__main__":
    main()