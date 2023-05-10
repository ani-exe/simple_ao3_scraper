#!/usr/bin/python3

# This is a simple script for parsing a bunch of fic metadata from
# a provided Ao3 search, and then stuffing it into a json. 
# I personally use this to do analysis in R Markdown, but you, dear friend
# can do whatever the hell you want. 

import sys, getopt, time
import json
import requests
from bs4 import BeautifulSoup


test_url = "https://archiveofourown.org/works?commit=Sort+and+Filter&work_search%5Bsort_column%5D=revised_at&work_search%5Bother_tag_names%5D=&work_search%5Bexcluded_tag_names%5D=&work_search%5Bcrossover%5D=F&work_search%5Bcomplete%5D=&work_search%5Bwords_from%5D=100&work_search%5Bwords_to%5D=&work_search%5Bdate_from%5D=&work_search%5Bdate_to%5D=&work_search%5Bquery%5D=&work_search%5Blanguage_id%5D=en&tag_id=%E3%83%A2%E3%83%96%E3%82%B5%E3%82%A4%E3%82%B3100+%7C+Mob+Psycho+100"

def _request_ao3(url, page=1):
    """
    Makes a request to ao3, returns structured metadata list.
    """
    success = False
    while not success:
        try:
            time.sleep(5) #need to wait 5 secs before req ao3 per TOS
            r = requests.get(url)
            if r.status_code is not 200:
                success = False
            else:
                return _parse_ao3_result_list(r.text)
        except Exception as e:
            print(str(e))


""""
i want an object like this, if possible:

title: title
description: desc
author: author:
id: id,
rating: (G, T, M, E, N)
relationships: (M/M, F/M, F/F, Multi, Other, Gen, None)
warning: (Chose_Not_To_Warn, Warning, No_Warning, External)
if_warning: (V, NC, U, MCD)
pairing: [either a & b, or a/b]
tags: [a, list, of, tags]
word_count: ###
chapter_count: ###
kudos: ###
hits: ###
comments: ###
finished: (t/f)
date_published: timestamp
date_updated: timestamp

"""

def _parse_ao3_result_list(html_str):
    """
    Uses beautiful soup to transform html into json with relevant metadata.
    Things I care about: title, author, id, rating, tags, pairings, description, warnings, 
    word count, chapters, kudos, hits, comments, date published, date updated
    """
    soup = BeautifulSoup(html_str, 'html.parser')
    # the list starts with <ol class="work index group">
    ls = soup.findall('li', class_="work blurb group")
    for work in ls:
        header = work.div
        link = header.h4.a
        id = link.get('href')
        title = link.string
        # this is fucked


    return







def main():
    # testing
    r = requests.get(test_url)
    with open('outfile', 'w') as f:
        f.write(r.text.encode('utf8'))

main()


# def main(argv):
#    search_url = ''
#    outputfile = ''
#    try:
#       opts, args = getopt.getopt(argv,"hu:o:",["url=","ofile="])
#    except getopt.GetoptError:
#       print ('test.py -u <search_url> -o <outputfile>')
#       sys.exit(2)
#    for opt, arg in opts:
#       if opt == '-h':
#          print ('test.py -u <search_url> -o <outputfile>')
#          sys.exit()
#       elif opt in ("-u", "--url"):
#          search_url = arg
#       elif opt in ("-o", "--ofile"):
#          outputfile = arg
#    print ('Input file is "', search_url)
#    print ('Output file is "', outputfile)
#    # do stuff with parsing here


# if __name__ == "__main__":
#    main(sys.argv[1:])