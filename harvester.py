import requests
import subprocess
import time
import json
from datetime import datetime
import sys
import argparse
from urllib.parse import urlparse
from pathlib import Path


def login_to_wiki(session, bot_username, bot_password, api_url):
    """login using bot credentials"""
    
    print(f"logging in as {bot_username}")
    
    # step 1: get login token
    try:
        token_response = session.get(api_url, params={
            'action': 'query',
            'meta': 'tokens',
            'type': 'login',
            'format': 'json'
        }, timeout=30)
        
        token_response.raise_for_status()
        token_data = token_response.json()
        
        if 'query' not in token_data or 'tokens' not in token_data['query']:
            raise Exception(f"failed to get login token: {token_data}")
        
        login_token = token_data['query']['tokens']['logintoken']
        print("got login token")
        
    except Exception as e:
        raise Exception(f"token request failed: {e}")
    
    # step 2: actual login
    try:
        login_response = session.post(api_url, data={
            'action': 'login',
            'lgname': bot_username,
            'lgpassword': bot_password,
            'lgtoken': login_token,
            'format': 'json'
        }, timeout=30)
        
        login_response.raise_for_status()
        login_result = login_response.json()
        
        if 'login' not in login_result:
            raise Exception(f"unexpected login response: {login_result}")
        
        result = login_result['login']['result']
        
        if result == 'Success':
            print(f"successfully logged in as {bot_username}")
            return session
        else:
            raise Exception(f"login failed: {result}")
            
    except Exception as e:
        raise Exception(f"login request failed: {e}")

def get_all_external_links(session, api_url, delay=2):
    """extract all external links from entire wiki"""
    
    all_external_urls = set()
    continue_param = None
    batch_count = 0
    
    print("starting external link extraction...")
    
    while True:
        params = {
            'action': 'query',
            'generator': 'allpages',  # get all pages
            'prop': 'extlinks',       # external links only
            'ellimit': 'max',         # max links per page
            'gaplimit': 50,           # 50 pages per batch
            'format': 'json'
        }
        
        if continue_param:
            params.update(continue_param)
        
        try:
            response = session.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # check for api errors
            if 'error' in data:
                print(f"api error: {data['error']}")
                if data['error']['code'] == 'readapidenied':
                    print("read access denied - check your bot permissions")
                break
                
            if 'query' in data and 'pages' in data['query']:
                for page_id, page in data['query']['pages'].items():
                    if 'extlinks' in page:
                        for link in page['extlinks']:
                            url = link['*']
                            # basic url validation
                            if url.startswith(('http://', 'https://')):
                                all_external_urls.add(url)
            
            batch_count += 1
            print(f"batch {batch_count}: {len(all_external_urls)} unique external urls found")
            
            # check if more pages exist
            if 'continue' not in data:
                break
                
            continue_param = data['continue']
            time.sleep(delay)  # rate limiting
            
        except Exception as e:
            print(f"error in batch {batch_count}: {e}")
            time.sleep(delay * 2)  # longer delay on error
            continue
    
    print(f"extraction complete: {len(all_external_urls)} total external links")
    return list(all_external_urls)

def save_urls(urls, filename):
    """save urls to file"""
    with open(filename, 'w') as f:
        f.write('\n'.join(urls))
    print(f"saved {len(urls)} urls to {filename}")

def main():
    # bot credentials
    bot_username = input("bot username:")  # format: username@botname
    bot_password = input("bot password:")  # from Special:BotPasswords
    api_url = input("api url:") #ends in /api.php
    
    # create session and login
    session = requests.Session()
    
    try:
        session = login_to_wiki(session, bot_username, bot_password, api_url)
    except Exception as e:
        print(f"login failed: {e}")
        return
    
    # extract all external links
    urls = get_all_external_links(session, api_url, delay=2)
    
    if not urls:
        print("no external links found")
        return
    
    # save raw list
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"links_{date_str}.txt"
    save_urls(urls, filename)
    
    print("done!")

if __name__ == "__main__":
    main()
