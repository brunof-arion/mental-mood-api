import boto3
import json
from botocore.exceptions import ClientError

def get_secret(secret_name, region_name):
    print(secret_name)
    print(region_name)
    # Create a Secrets Manager client
    client = boto3.client('secretsmanager', region_name=region_name)

    try:
        # Retrieve the secret value
        response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        # Handle exceptions
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # The requested secret was not found
            raise e
    else:
        # Secrets Manager returned the secret value
        if 'SecretString' in response:
            secret = response['SecretString']
        else:
            secret = response['SecretBinary']

        # If the secret is in JSON format, parse it
        try:
            return json.loads(secret)
        except json.JSONDecodeError:
            return secret