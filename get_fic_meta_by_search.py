#!/usr/bin/python3

# This is a simple script for parsing a bunch of fic metadata from
# a provided Ao3 search, and then stuffing it into a json. 
# I personally use this to do analysis in R Markdown, but you, dear friend
# can do whatever the hell you want. 

import sys, getopt, time
import json
import requests
from bs4 import BeautifulSoup

"""
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
            if r.status_code != 200:
                success = False
            else:
                return _parse_ao3_result_list(r.text)
        except Exception as e:
            print(str(e))


def _stat_parse_helper(stat_object, class_name):
    find_stat = stat_object.find('dd', class_=class_name)
    find_stat = int(find_stat.text.replace(',', '')) if find_stat else 0
    return find_stat


def _parse_ao3_result_list(html_str):
    """
    Uses beautiful soup to transform html into json with relevant metadata.
    Things I care about: title, author, id, rating, tags, pairings, description, warnings, 
    word count, chapters, kudos, hits, comments, date published, date updated
    """
    soup = BeautifulSoup(html_str, 'html.parser')
    work_index_group = soup.find('ol', class_="work index group")
    works = work_index_group.find_all('li', class_="work")

    jsons = []
    for work in works:
        header = work.div
        link = header.h4.a
        author = link.find_next().text
        id_ = link.get('href')
        title = link.string

        required_tags = header.find('ul', class_="required-tags")

        tag_lis = required_tags.find_all('li')
        rating = tag_lis[0].a.text
        warnings = tag_lis[1].a.text.split(', ')
        category = tag_lis[2].a.text.split(', ')
        is_wip = tag_lis[3].a.text == "Work in Progress"

        last_updated = header.find('p', class_="datetime").text
        # so fucking annoying i can't get more specific timestamp here todo ani look into that

        tags_commas = work.find('ul', class_="tags commas")
        relationships = tags_commas.find_all('li', class_="relationships")
        is_slash = False
        if relationships:
            relationships = [r.a.text for r in relationships]
            is_slash = True if any('/' in r for r in relationships) else False
        freeforms = tags_commas.find_all('li', class_="freeforms")
        if freeforms:
            freeforms = [f.a.text for f in freeforms]
        
        summary = work.find('blockquote', class_="userstuff summary")
        # todo ani: do i care about breaking this down? contains links? etc etc
        
        #series = work.find('ul', class_="series")
        # find example of multiple series work for testing
        # they are all li in a ul e.g:
        #<ul class="series">
        #<li>
        #  Part <strong>1</strong> of <a href="/series/1756675">Off to the Races</a>
        #</li>
        #</ul>
        # todo ani collect whether or not the work is in a series
        # do i care??? maybe????

        stats_all = work.find('dl', class_="stats")
        language = stats_all.find('dd', class_="language").text
        words = _stat_parse_helper(stats_all, 'words')
        
        chapters = stats_all.find('dd', class_="chapters").text.split('/')
        cur_chapters = int(chapters[0].replace(',', ''))
        intended_chapters = chapters[1]

        
        kudos = _stat_parse_helper(stats_all, 'kudos')
        hits = _stat_parse_helper(stats_all, 'hits')
        comments = _stat_parse_helper(stats_all, 'comments')
        collections = _stat_parse_helper(stats_all, 'collections')
        # todo ani do i care about the collection meta???? not sure?? need example
        bookmarks = _stat_parse_helper(stats_all, 'bookmarks')

        jsons.append({
            "title": title,
            "author": author,
            "id": id_,
            "rating": rating,
            "warnings": warnings,
            "category": category,
            "iswip": is_wip,
            "lastUpdated": last_updated,
            "relationships": relationships,
            "isslash": is_slash,
            "freeforms": freeforms,
            "summary": summary,
            "language": language,
            "words": words,
            "currentChapters": cur_chapters,
            "intendedChapters": intended_chapters,
            "kudos": kudos,
            "hits": hits,
            "comments": comments,
            "bookmarks": bookmarks,
            "collections": collections,
        })

    return jsons


def main():
    #r = requests.get(test_url)
    #with open('outfile', 'w', encoding='utf8') as f:
    #    f.write(r.text)

    with open('outfile', 'r', encoding='utf8') as f:
        html = f.read()

    result_list = _parse_ao3_result_list(html)
    #for rl in result_list:
    #    print(rl)
    #    print()

if __name__ == "__main__":
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
