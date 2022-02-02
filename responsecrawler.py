# -*- coding: utf-8 -*-

from seleniumwire import webdriver
from bs4 import BeautifulSoup
import requests
import re
from datetime import datetime
import json
import logging

def getSiteDomain(url):
    try:
        domain = re.split('https*://', url)[1].split('/')[0]
        return url[:re.search(domain, url).start()]+domain
        
    except Exception as e:
        logger.error(e)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
chrome_ext = "C:\chromedriver_win32\chromedriver.exe"
keys = ['page_url', 'status_code', 'page_title', 'referrer', 'responses']
result = list()

try:
    init_url = input("Enter the url begins with 'https://' or 'http://' : ").strip()
    pagelimit = int(input("Enter the max number of pages to scan : "))

    logFileName = '{}({})'.format(datetime.today().strftime("%Y%m%d_%H%M%S"), init_url.split('://')[1].split('/')[0] )
    logger.addHandler(logging.FileHandler(logFileName+'.txt'))
    
    if re.match('https*://', init_url) == None:
        raise Exception("ERROR - Initial URL must begin with 'https://' or 'http://'")
    elif init_url == 'https://' or init_url == 'http://':
        raise Exception("ERROR - Site url is missing")
    else:
        site_domain = getSiteDomain(init_url)
except Exception as e:
    if type(e).__name__ == 'ValueError':
        logger.error("ERROR - Enter integer for page limit")
    else:
        logger.error(e)

pagelist = [[init_url], ['initial url']]

for i, page in enumerate(pagelist[0]):
   if i<pagelimit:
      try:      
         result.append(dict.fromkeys(keys))
         valStatusCode = requests.get(page).status_code
         result[i]['page_url'] = page
         result[i]['status_code'] = valStatusCode
         result[i]['page_title'] = ''
         result[i]['referrer'] = pagelist[1][i]
         result[i]['responses'] = []

         logger.info("({}/{}){}|{}".format((i+1), len(pagelist[0]), valStatusCode, page))

         if valStatusCode >= 200 and valStatusCode < 400:

               driver = webdriver.Chrome(chrome_ext)
               driver.get(page)
               result[i]['page_title']=driver.title
            
               if page.startswith(site_domain):
                  src = driver.page_source
                  soup = BeautifulSoup(src)
                  links = soup.find_all('a', href=True)

                  logger.info('{} link(s) found'.format(len(links)))
                  for link in links:
                     
                     msg = '{} ------> '.format(link['href'])

                     if str(link['href']) == '/' or str(link['href']) == '#':
                        msg += 'Duplicated link'
                        continue
                     else:
                        isExist = 0
                        full_url = site_domain+str(link['href']) if str(link['href']).startswith('/') else str(link['href'])
                        last_path = full_url.split("?")[0].split('/')[-1]
                        
                        if pagelist[0].count(full_url)>0:
                           isExist = 1
                           msg += 'Duplicated link'
                        else:
                           if last_path.isnumeric() or (any(map(str.isdigit, last_path)) and re.search(r'[0-9a-fA-F]{16}', last_path) is not None):
                              check_url = full_url[:full_url.rfind('/')]
                           else:
                              check_url = full_url.split("?")[0]
                           
                           similar_urls = filter(lambda x: x.startswith(check_url), pagelist[0])
                           
                           if len(list(similar_urls)) >= 10:
                              isExist = 1
                              msg += "Similar urls are queued in the list 10 times ({}...)".format(check_url)

                        if isExist == 0:
                           msg += "ADDED in the list"
                           pagelist[0].append(full_url)
                           pagelist[1].append(page)
                        
                        logger.info(msg)

                  for req in driver.requests:
                     if req.response.status_code >= 400:
                        contentType = ' | '+req.response.headers['Content-Type'].split(';')[0] if req.response.headers['Content-Type'] is not None else ''
                        result[i]['responses'].append('[{}{}] {}'.format(req.response.status_code, contentType, req.url))

                  driver.close()
      except Exception as e:
         logger.error(e)
   else:
      break

r = {"data":result}

f = open(logFileName+".json", "w")
json.dump(r, f)
f.close()