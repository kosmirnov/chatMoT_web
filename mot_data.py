import os
import requests
import logging
from dotenv import load_dotenv
from typing import Optional, Dict, Any

class MotData:
    """A class to fetch MoT data and generate a summary."""

    def __init__(self, registration: str):
        """Initializes the MotData class."""
        self.registration = registration
        load_dotenv()
        self.TOKEN_URL = os.getenv("token_url")
        self.CLIENT_ID = os.getenv("client_id")
        self.CLIENT_SECRET = os.getenv("client_secret")
        self.SCOPE_URL = os.getenv("scope_url")
        self.API_KEY = os.getenv("api_key")
        self.access_token = self.get_access_token()  # Get token synchronously


    def get_access_token(self) -> Optional[str]:
        """Fetches an access token from the MoT API synchronously."""
        token_data = {
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "scope": self.SCOPE_URL,
            "grant_type": "client_credentials"
        }

        try:
            response = requests.post(self.TOKEN_URL, data=token_data)
            response.raise_for_status()
            return response.json().get("access_token")
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Error obtaining access token: {e}")
            return None

    def fetch_vehicle_data(self) -> Optional[Dict[str, Any]]:
        """Fetches MoT history for a given vehicle registration number synchronously."""
        if not self.access_token:
            logging.error("❌ No access token available. Unable to fetch vehicle data.")
            return None

        API_URL = f"https://history.mot.api.gov.uk/v1/trade/vehicles/registration/{self.registration}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "X-Api-Key": self.API_KEY
        }

        try:
            response = requests.get(API_URL, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Error fetching vehicle data: {e}")
            return None

    def validate_mot_test(self, test: Dict[str, Any]) -> bool:
        if not isinstance(test, dict):
            logging.error(f"❌ Invalid MoT test data: Expected a dictionary, got {type(test)}")
            return False
        if 'completedDate' not in test or not isinstance(test['completedDate'], str):
            logging.error("❌Invalid or missing 'completedDate' in MoT test")
            return False
        if 'testResult' not in test or test['testResult'] not in ['PASSED', 'FAILED']:  # add valid values
            logging.error("❌Missing or Invalid 'testResult' in MOT test")
            return False

        if 'odometerValue' in test:
            try:
                int(test['odometerValue'])  # try casting to int
            except ValueError:
                logging.error("❌ Non-numeric odometerValue found")
                return False
        return True


    def generate_mot_summary(self) -> str:
        """Generates an MoT summary from the vehicle data synchronously."""
        vehicle_data = self.fetch_vehicle_data()
        if not vehicle_data or "motTests" not in vehicle_data or not vehicle_data["motTests"]:
            logging.warning(
                f"⚠️ No MoT test data available for vehicle registration: {self.registration}")
            return "No MoT test data available for this vehicle."

        try:
            mot_summary = f"Vehicle Registration: {vehicle_data.get('registration', 'Unknown')}\n"
            mot_summary += f"Make: {vehicle_data.get('make', 'Unknown')}\n"
            mot_summary += f"Model: {vehicle_data.get('model', 'Unknown')}\n"
            mot_summary += f"First Registered: {vehicle_data.get('firstUsedDate', 'Unknown')}\n\n"
            mot_summary += "MoT Test History:\n"

            for test in vehicle_data["motTests"]:
                # Validate each MOT test before processing
                if not self.validate_mot_test(test):
                    logging.warning(f"⚠️ Skipping invalid MOT test due to validation failure: {test}")
                    continue  # Skip to the next test

                mot_summary += f"- Test Date: {test.get('completedDate', 'N/A')}, "
                mot_summary += f"Result: {'Pass ✅' if test.get('testResult') == 'PASSED' else 'Fail ❌'}\n"
                mot_summary += f"  Mileage: {test.get('odometerValue', 'N/A')} {test.get('odometerUnit', '')}\n"

                for i in test.get('defects', []):
                    mot_summary += f"  Defect: {i.get('text', 'N/A')} (Type: {i.get('type', 'N/A')}, Dangerous: {i.get('dangerous', 'N/A')})\n"
            return mot_summary

        except KeyError as e:
            logging.error(f"❌ KeyError while generating MoT summary: {e}. Check API response structure.")
            return "An error occurred while generating the MoT summary."