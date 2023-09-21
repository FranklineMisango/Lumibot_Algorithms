from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

vault_url = "https://alogbeta.vault.azure.net/"
secret_name_one = "ALPACAKEY"
secret_name_two = "ALPACASECRETKEY"
secret_name_three = "APCAAPIBASEURL"

credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=vault_url, credential=credential)

# Retrieve the secret
secret_value_one = secret_client.get_secret(secret_name_one).value
secret_value_two = secret_client.get_secret(secret_name_two).value
secret_value_three = secret_client.get_secret(secret_name_three).value


#The trading infrasctracture 
ALPACAKEY = secret_value_one
ALPACASECRETKEY = secret_value_two
APCAAPIBASEURL = secret_value_three
