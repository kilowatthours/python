import jwt
import json
import requests
import boto3
from jwt import PyJWKClient

def is_valid_token(bearer_token, audience):
    print('Validating token...')
    web_key_set_uri = "https://login.microsoftonline.com/common/discovery/keys"
    jwks_client = PyJWKClient(web_key_set_uri)
    signing_key = jwks_client.get_signing_key_from_jwt(bearer_token)
    
    result = {}
    try:
        decoded_token = jwt.decode(bearer_token, signing_key.key, algorithms=["RS256"], audience=audience, options={"verify_exp": False})
        result = True
    except Exception as error:
        print(error)
        result = False
    finally:
        print('Token validated')
        return result

def get_secrets():
    print('Getting secrets...')
    secret_name = "test/opportunity-ecosys-producer/aad-client-credentials"
    
    client = boto3.client('secretsmanager')

    get_secret_value_response = client.get_secret_value(
        SecretId=secret_name    
    )
    text_secret_data = json.loads(get_secret_value_response['SecretString'])
    secrets={
        "azure_client_id": text_secret_data['aad-client-id'],
        "azure_client_secret": text_secret_data['aad-client-secret'],
        "audience": f"api://{text_secret_data['aad-client-id']}"
    }
    print('Got Secrets')
    return secrets

def generate_policy(is_valid, methodArn):
    policy = {
      "principalId": "user",
      "policyDocument": {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Action": "execute-api:Invoke",
            "Effect": "Allow" if is_valid else "Deny",
            "Resource": methodArn
          }
        ]
      }
    }
    return policy

def lambda_handler(event, context):
    print(event)
    bearer_token = event["authorizationToken"].split(" ")[1]
    client_secrets = get_secrets()
    is_valid = is_valid_token(bearer_token, client_secrets['audience'])
    policy = generate_policy(is_valid, event['methodArn'])
    return policy
