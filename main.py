import schedule
import time
import datetime
import requests
import xml.etree.ElementTree as ET
import json
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Global variable to track the latest published post's timestamp for each feed
latest_pub_dates = {}

# List of RSS feed URLs
rss_urls = [
    "https://www.bdstory.net/feeds/posts/default?alt=rss",
    "https://www.bdmiti.com/feeds/posts/default?alt=rss",
    # Add more feed URLs as needed
]

# Load the token from a file if it exists
token_filename = './token/token.json'
try:
    with open(token_filename, 'r') as token_file:
        token_json = token_file.read()
        credentials = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
except FileNotFoundError:
    # If the token file doesn't exist, start the authorization flow
    SCOPES = ['https://www.googleapis.com/auth/blogger']
    flow = InstalledAppFlow.from_client_secrets_file('./path/client_secret.json', SCOPES)
    credentials = flow.run_local_server(port=0)

    # Save the token to a file after the initial authorization
    with open(token_filename, 'w') as token_file:
        token_file.write(credentials.to_json())

# Build the Blogger API service
service = build('blogger', 'v3', credentials=credentials)


def fetch_and_publish(rss_url):
    global latest_pub_dates

    # Fetch the RSS feed content
    response = requests.get(rss_url)
    rss_content = response.text

    # Parse the XML content
    xml = ET.fromstring(rss_content)

    # Loop through the RSS feed items and post to Blogger
    for item in xml.findall('.//channel/item'):
        title = item.find('title').text
        content = item.find('description').text  # Change this to 'content' if applicable
        pub_date_str = item.find('pubDate').text
        pub_date = datetime.datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
        pub_date = pub_date.replace(tzinfo=datetime.timezone.utc)

        # Calculate the time difference in seconds
        time_difference = (datetime.datetime.now(datetime.timezone.utc) - pub_date).total_seconds()

        # Check if the post was published within the last 1 hour (3600 seconds)
        if rss_url not in latest_pub_dates:
            latest_pub_dates[rss_url] = None

        if latest_pub_dates[rss_url] is None or time_difference <= 18000:
            # Create a new blog post
            post = {
                "title": title,
                "content": content
            }

            # Execute the API request to create a post
            request = service.posts().insert(blogId='3009691482324718775', body=post)
            response = request.execute()

            print(f"Posted from {rss_url}: {title} - {response['url']}")

            # Update the latest_pub_date for this feed if needed
            if latest_pub_dates[rss_url] is None or pub_date > latest_pub_dates[rss_url]:
                latest_pub_dates[rss_url] = pub_date


# Schedule the fetch_and_publish function for each RSS feed URL
for rss_url in rss_urls:
    schedule.every(2).minutes.do(fetch_and_publish, rss_url)

while True:
    schedule.run_pending()
    time.sleep(10)
