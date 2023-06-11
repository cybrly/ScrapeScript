import requests
from bs4 import BeautifulSoup
import re
import codecs
import argparse
from urllib.parse import urlparse, urljoin
from colorama import init, Fore
from email_validator import validate_email, EmailNotValidError  # additional library for email validation
from multiprocessing import Process, Event
import time


# session creation
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})


def add_http(url):
    if not re.match('(?:http|https)://', url):
        return 'http://' + url
    return url


def decode_rot13(encoded_email):
    return codecs.decode(encoded_email, 'rot_13')


def is_valid(url, domain):
    parsed = urlparse(url)
    return bool(parsed.netloc) and parsed.netloc.endswith(domain)


def print_email(email, domain, file, mail_ids):
    if email not in mail_ids:
        email_domain = email.split('@')[-1]
        if email_domain == domain:
            output = Fore.GREEN + email + Fore.RESET  # print in green
        else:
            output = email

        print(output)
        if file:
            with open(file, 'a') as f:
                f.write(output + '\n')
                
        mail_ids.add(email)


# modification to get_links function to use session
def get_links(url):
    response = session.get(url, timeout=5)  # Set a timeout of 5 seconds for the request
    soup = BeautifulSoup(response.text, 'html.parser')
    for a in soup.find_all('a', href=True):
        yield a['href']


# modified scrape_emails to handle exceptions and use extract_and_validate_emails function
def scrape_emails(url, depth, output_file, exit_event):
    url = add_http(url)
    domain = urlparse(url).netloc
    urls_to_visit = [(url, 0)]
    visited_urls = set()

    mail_ids = set()
    mail_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    rot13_regex = r'swrot13\(\'(.*?)\'\)'

    start_time = time.time()
    while urls_to_visit:
        current_url, current_depth = urls_to_visit.pop()
        visited_urls.add(current_url)

        try:
            response = session.get(current_url, timeout=5)  # Set a timeout of 5 seconds for the request
            soup = BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as e:
            print(f"An error occurred when trying to get {current_url}: {str(e)}")
            continue

        for tag in soup.find_all():
            emails = extract_and_validate_emails(tag, mail_regex, rot13_regex, domain, output_file, mail_ids)
            mail_ids.update(emails)

        if current_depth < depth:
            for link in get_links(current_url):
                new_url = urljoin(current_url, link)
                if is_valid(new_url, domain) and new_url not in visited_urls:
                    urls_to_visit.append((new_url, current_depth + 1))
        
        if time.time() - start_time > 30:
            exit_event.set()
            break


# new function for email extraction and validation
def extract_and_validate_emails(tag, mail_regex, rot13_regex, domain, output_file, mail_ids):
    emails_set = set()

    rot13_encoded_emails = re.findall(rot13_regex, str(tag))
    for encoded_email in rot13_encoded_emails:
        decoded_email = decode_rot13(encoded_email)
        # using email-validator library for validation
        try:
            v = validate_email(decoded_email)
            decoded_email = decoded_email.lower()
            print_email(decoded_email, domain, output_file, mail_ids)
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
                print_email(email, domain, output_file, mail_ids)
                emails_set.add(email)
            except EmailNotValidError as e:
                # email is not valid, nothing to do
                pass

    return emails_set


if __name__ == "__main__":
    init()  # initialize colorama
    parser = argparse.ArgumentParser(description="Scrape a webpage for email addresses.")
    parser.add_argument("url", help="The domain to scrape.")
    parser.add_argument("-d", "--depth", type=int, help="The maximum depth to follow links.", default=1)
    parser.add_argument("-o", "--output", type=str, help="File to save the scraped emails.", default=None)
    args = parser.parse_args()

    exit_event = Event()
    p = Process(target=scrape_emails, args=(args.url, args.depth, args.output, exit_event))
    p.start()

    start_time = time.time()
    while True:
        p.join(timeout=1)
        if not p.is_alive():
            break
        if time.time() - start_time > 30:
            print("No new emails found. Exiting...")
            exit_event.set()
            break