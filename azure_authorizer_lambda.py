import json
import jwt
import requests
import os

def lambda_handler(event, context):
    print(event)
    # Get the JWT token from the headers
    jwt_token = event["headers"]["Authorization"].split(" ")[1]

    # Get the audience ID from the environment variables
    audience = os.environ["AUDIENCE_ID"]
    azure_tenant_id = os.environ["AZURE_TENANT_ID"]
    azure_client_id = os.environ["AZURE_CLIENT_ID"]
    azure_client_secret = os.environ["AZURE_CLIENT_SECRET"]

    # Get an access token from Azure AD
    try:
        # Get the access token from Azure AD
        azure_token_url = f"https://login.microsoftonline.com/{azure_tenant_id}/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": azure_client_id,
            "client_secret": azure_client_secret,
            "resource": "https://management.azure.com/",
        }
        response = requests.post(azure_token_url, data=data)
        response.raise_for_status()
        access_token = response.json()["access_token"]
    except requests.exceptions.HTTPError as http_err:
        return {
            "statusCode": http_err.response.status_code,
            "body": json.dumps({"error": http_err.response.text})
        }
    except Exception as err:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(err)})
        }

    # Verify the JWT token using the access token
    try:
        azure_validation_url = f"https://management.azure.com/providers/Microsoft.AAD/validateJWT?api-version=2019-08-01"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        data = {"jwt": jwt_token, "audience": audience}
        response = requests.post(azure_validation_url, headers=headers, json=data)
        response.raise_for_status()
        validation_response = response.json()
    except requests.exceptions.HTTPError as http_err:
        return {
            "statusCode": http_err.response.status_code,
            "body": json.dumps({"error": http_err.response.text})
        }
    except Exception as err:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(err)})
        }

    # If the JWT token is valid, return the validation response
    #if validation_response["isValid"]:
    #    return {
    #        "statusCode": 200,
    #        "body": json.dumps(validation_response)
    #    }
    #else:
    #    return {
    #        "statusCode": 403,
    #        "body": json.dumps({"error": "Invalid token"})
    
    if validation_response["isValid"]:
        # Return the principal ID and policy document for the authenticated user
        return {
            "principalId": validation_response["userId"],
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "execute-api:Invoke",
                        "Effect": "Allow",
                        "Resource": event["methodArn"]
                    }
                ]
            }
        }
    else:
        return {
            "statusCode": 403,
            "body": json.dumps({"error": "Invalid token"})
        }