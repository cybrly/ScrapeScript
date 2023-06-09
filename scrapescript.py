import requests
from bs4 import BeautifulSoup
import re
import sys
import codecs
import argparse
from urllib.parse import urlparse, urljoin
from tqdm import tqdm
from colorama import init, Fore


def add_http(url):
    if not re.match('(?:http|https)://', url):
        return 'http://' + url
    return url


def decode_rot13(encoded_email):
    return codecs.decode(encoded_email, 'rot_13')


def is_valid(url, domain):
    parsed = urlparse(url)
    return bool(parsed.netloc) and parsed.netloc.endswith(domain)


def get_links(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    for a in soup.find_all('a', href=True):
        yield a['href']


def print_email(email, domain):
    email_domain = email.split('@')[-1]
    if email_domain == domain:
        print(Fore.GREEN + email + Fore.RESET)  # print in green
    else:
        print(email)


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

            response = requests.get(current_url)
            soup = BeautifulSoup(response.text, 'html.parser')

            for tag in soup.find_all():
                # Find ROT13 encoded emails
                rot13_encoded_emails = re.findall(rot13_regex, str(tag))
                for encoded_email in rot13_encoded_emails:
                    decoded_email = decode_rot13(encoded_email)
                    # Validate that the decoded email is a proper email format before adding
                    if re.match(mail_regex, decoded_email):
                        # Convert email to lowercase to handle different capitalizations
                        decoded_email = decoded_email.lower()
                        if decoded_email not in mail_ids:
                            print_email(decoded_email, domain)
                            mail_ids.add(decoded_email)

                # Find normal emails
                if not rot13_encoded_emails:
                    emails = re.findall(mail_regex, str(tag))
                    for email in emails:
                        # Convert email to lowercase to handle different capitalizations
                        email = email.lower()
                        if email not in mail_ids:
                            print_email(email, domain)
                            mail_ids.add(email)

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