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
defaultkeys = ['page_url', 'status_code', 'referrer']
result = {"OK" : [], "NOK" : []}


# DEFINE A LIST OF KNOWN/EXCEPTONAL ERRORS IN THE FORM OF REGULAR EXPRESSION, THEN IT WILL BE IGNORED
# IF THERE IS NOTHING, LEAVE IT AS EMPTY LIKE THIS.
# exceptionalErrors = {
#    "console_error" : []
#    , "response_error" : []
#    }
exceptionalErrors = {
   "console_error" : [
      "requested an insecure resource 'http:\/\/static\.yoursite\.com\.s3\.ap-northeast-2\.amazonaws\.com\/translation\/ko_KR\/ko_KR\.json'\.",
      "^(https:\/\/s3\.ap-northeast-2\.amazonaws\.com\/yoursite-public\/logo\/)"
      ]
   , "response_error" : [
      "^(https:\/\/s3\.ap-northeast-2\.amazonaws\.com\/yoursite-public\/logo\/)"
      ]
   }

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
         temp_result = dict.fromkeys(defaultkeys)
         valStatusCode = requests.get(page).status_code
         temp_result['page_url'] = page
         temp_result['status_code'] = valStatusCode
         temp_result['referrer'] = pagelist[1][i]
         
         logger.info("({}/{}){}|{}".format((i+1), len(pagelist[0]), valStatusCode, page))

         if valStatusCode in range(200, 400) and page.startswith(site_domain):
            options = webdriver.ChromeOptions()
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            driver = webdriver.Chrome(chrome_ext, options=options)

            driver.get(page)
            temp_result['page_title']=driver.title

            # CAPTURE REQUEST ERRORS
            for req in driver.requests:
               if req.response.status_code >= 400:
                  isExceptionalError = 0
                  for i in exceptionalErrors['response_error']:
                     if re.search(i, req.url) != None : isExceptionalError=1
                  if isExceptionalError == 0:
                     contentType = ' | '+req.response.headers['Content-Type'].split(';')[0] if req.response.headers['Content-Type'] is not None else ''
                     if 'response_error' in temp_result.keys():
                        temp_result['response_error'].append('[{}{}] {}'.format(req.response.status_code, contentType, req.url))
                     else:
                        temp_result['response_error'] = ['[{}{}] {}'.format(req.response.status_code, contentType, req.url)]
                     logger.error("Error - Response Error")
                  else:
                     logger.warning("Warning - Exceptional Response Error")
            
            # CAPTURE CONSOLE ERRORS
            for log in driver.get_log("browser"):
               if log['level']=='SEVERE':
                  isExceptionalError = 0
                  for i in exceptionalErrors['console_error']:
                     if re.search(i, log['message']) != None : isExceptionalError=1
                  if isExceptionalError == 0 :
                     if 'console_error' in temp_result.keys():
                        temp_result['console_error'].append(log)
                     else:
                        temp_result['console_error'] = [log]     
                     logger.error("Error - Console Error")
                  else:
                     logger.warning("Warning - Exceptional Console Error")

            if 'response_error' in temp_result.keys() or 'console_error' in temp_result.keys():
               result['NOK'].append(temp_result)
            else:
               result['OK'].append(temp_result)                

            # FIND AND QUEUE LINKS
            src = driver.page_source
            soup = BeautifulSoup(src, "html.parser")
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
                     if last_path.isnumeric() or (any(map(str.isdigit, last_path)) and re.search(r'[0-9a-fA-F-_]{6}', last_path) is not None):
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

            driver.close()
         else:
            result['NOK'].append(temp_result)
      except Exception as e:
         logger.error(e)
   else:
      break

f = open(logFileName+".json", "w")
json.dump(result, f)
f.close()

logger.handlers.clear()
