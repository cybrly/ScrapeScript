import requests
from bs4 import BeautifulSoup
import re
import sys
import codecs
import argparse
from urllib.parse import urlparse, urljoin
from tqdm import tqdm
from colorama import init, Fore
from email_validator import validate_email, EmailNotValidError # additional library for email validation

# session creation
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

# new function for email extraction and validation
def extract_and_validate_emails(tag, mail_regex, rot13_regex, domain):
    emails_set = set()

    rot13_encoded_emails = re.findall(rot13_regex, str(tag))
    for encoded_email in rot13_encoded_emails:
        decoded_email = decode_rot13(encoded_email)
        # using email-validator library for validation
        try:
            v = validate_email(decoded_email)
            decoded_email = decoded_email.lower()
            print_email(decoded_email, domain)
            emails_set.add(decoded_email)
        except EmailNotValidError as e:
            # email is not valid, nothing to do
            pass

    # Find normal emails
    if not rot13_encoded_emails:
        emails = re.findall(mail_regex, str(tag))
        for email in emails:
            try:
                v = validate_email(email)
                email = email.lower()
                print_email(email, domain)
                emails_set.add(email)
            except EmailNotValidError as e:
                # email is not valid, nothing to do
                pass

    return emails_set

# modification to get_links function to use session
def get_links(url):
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    for a in soup.find_all('a', href=True):
        yield a['href']

# modified scrape_emails to handle exceptions and use extract_and_validate_emails function
def scrape_emails(url, depth):
    url = add_http(url)
    domain = urlparse(url).netloc
    urls_to_visit = [(url, 0)]
    visited_urls = set()

    mail_ids = set()
    mail_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    rot13_regex = r'swrot13\(\'(.*?)\'\)'

    with tqdm(total=depth, position=0, bar_format='{l_bar}{bar}| {remaining}', desc='Processing URLs', disable=True) as pbar:
        while urls_to_visit:
            current_url, current_depth = urls_to_visit.pop()
            visited_urls.add(current_url)

            try:
                response = session.get(current_url)
                soup = BeautifulSoup(response.text, 'html.parser')
            except requests.exceptions.RequestException as e:
                print(f"An error occurred when trying to get {current_url}: {str(e)}")
                continue

            for tag in soup.find_all():
                mail_ids.update(extract_and_validate_emails(tag, mail_regex, rot13_regex, domain))

            if current_depth < depth:
                for link in get_links(current_url):
                    new_url = urljoin(current_url, link)
                    if is_valid(new_url, domain) and new_url not in visited_urls:
                        urls_to_visit.append((new_url, current_depth + 1))

            pbar.update(1)

if __name__ == "__main__":
    init()  # initialize colorama
    parser = argparse.ArgumentParser(description="Scrape a webpage for email addresses.")
    parser.add_argument("url", help="The domain to scrape.")
    parser.add_argument("-d", "--depth", type=int, help="The maximum depth to follow links.", default=1)
    args = parser.parse_args()

    scrape_emails(args.url, args.depth)