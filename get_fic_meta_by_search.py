#!/usr/bin/python3

# This is a simple script for parsing a bunch of fic metadata from
# a provided Ao3 search, and then stuffing it into a json. 
# I personally use this to do analysis in R Markdown, but you, dear friend
# can do whatever the hell you want. 

import sys, getopt, time
import json
import re
import requests
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup


# This URL does a search for MP100 works in English, 
# excluding crossovers and works under 100 words
# and returns the list by date updated
base_url = "https://archiveofourown.org/works?commit=Sort+and+Filter&work_search%5Bsort_column%5D=revised_at&work_search%5Bother_tag_names%5D=&work_search%5Bexcluded_tag_names%5D=&work_search%5Bcrossover%5D=F&work_search%5Bcomplete%5D=&work_search%5Bwords_from%5D=100&work_search%5Bwords_to%5D=&work_search%5Bdate_from%5D=&work_search%5Bdate_to%5D=&work_search%5Bquery%5D=&work_search%5Blanguage_id%5D=en&tag_id=%E3%83%A2%E3%83%96%E3%82%B5%E3%82%A4%E3%82%B3100+%7C+Mob+Psycho+100"

"""
page two of above looks like this:
https://archiveofourown.org/tags/%E3%83%A2%E3%83%96%E3%82%B5%E3%82%A4%E3%82%B3100%20%7C%20Mob%20Psycho%20100/works?commit=Sort+and+Filter&page=2&work_search%5Bcomplete%5D=&work_search%5Bcrossover%5D=F&work_search%5Bdate_from%5D=&work_search%5Bdate_to%5D=&work_search%5Bexcluded_tag_names%5D=&work_search%5Blanguage_id%5D=en&work_search%5Bother_tag_names%5D=&work_search%5Bquery%5D=&work_search%5Bsort_column%5D=revised_at&work_search%5Bwords_from%5D=100&work_search%5Bwords_to%5D=

notice &page=2 url param, means we index from 1, not 0.
additionally, b/c parsing takes so long, i need to keep a set of story ids to dedupe
in case someone publishes something new while i'm parsing and sets me off-by-one
"""

# This is a test search I used b/c I knew it had Anonymous and Collections examples
# Don't use for main stat collection
test_url_contains_anonymous = "https://archiveofourown.org/works?commit=Sort+and+Filter&work_search%5Bsort_column%5D=revised_at&include_work_search%5Brating_ids%5D%5B%5D=13&include_work_search%5Brelationship_ids%5D%5B%5D=10483645&work_search%5Bother_tag_names%5D=&work_search%5Bexcluded_tag_names%5D=&work_search%5Bcrossover%5D=&work_search%5Bcomplete%5D=&work_search%5Bwords_from%5D=&work_search%5Bwords_to%5D=&work_search%5Bdate_from%5D=&work_search%5Bdate_to%5D=&work_search%5Bquery%5D=&work_search%5Blanguage_id%5D=&tag_id=%E3%83%A2%E3%83%96%E3%82%B5%E3%82%A4%E3%82%B3100+%7C+Mob+Psycho+100"

works_base_url= "https://archiveofourown.org{}"

with open ('canonical_tags.json', 'r') as f:
    ctjson = json.load(f)

unique_ids = set()
canonical_tag_ids = set(ctjson['list'])
print(canonical_tag_ids)

def process_ao3_loop():

    # this needs to loop until we hit the end of the searchable archive
    # what's the best way to determine the end?
    # could be two things -- either we get < 20 items or we get nothing
    # whichever comes first

    # todo ani, update this later to allow contributed url, not just base

    page = 310
    full_results_list = []
    while True: 
        page_param = '&page={page}'.format(page=page)
        url_with_page = base_url + page_param
        print('requesting', url_with_page)
        res = _request_ao3(url_with_page)
        full_results_list += res
        
        if not res: # we might dedupe some items so checking num items isn't accurate
            print('last page is', page)
            break # should mean we're done here
        
        page += 1

    return full_results_list

def _request_ao3(url):
    """
    Makes a request to ao3, returns structured metadata list for page.
    """
    success = False
    allowable_tries = 3 #if exceeds this, just give up
    tries = 0

    while not success:
        if tries >= allowable_tries:
            break
        try:
            time.sleep(5) #need to wait 5 secs before req ao3 per TOS
            # todo ani, need exponential backoff? let's see
            tries += 1
            r = requests.get(url)
            if r.status_code != 200:
                success = False
            else:
                return _parse_ao3_result_list(r.text)
        except Exception as e:
            print(str(e))
    
    # if we get here, something went wrong and we need to abort mission
    # might be blocked, rate limited, or ao3 might be Having Problems
    # or ani can't code. idk
    print(r.status_code)
    print(r.text)
    sys.exit("something went horribly wrong, fix it")


def _stat_parse_helper(stat_object, class_name):
    find_stat = stat_object.find('dd', class_=class_name)
    if find_stat:
        find_stat = int(find_stat.text.replace(',', '')) if find_stat else 0
        return find_stat
    else:   
        return 0
    
def _wrangle_relationship_tags(rel_list):
    global canonical_tag_ids
    rel_tags = ('*s*', '*a*')
    # todo slash is indicated in link with *s* and & with *a*
    # so i can grab the relationships by url decoding the tags
    # and replacing the symbols
    # "/tags/Reigen%20Arataka*s*Serizawa%20Katsuya/works" eg
    # sigh we got stuck at 310
    # need exponential backoff
    # and need to write out the json even if we fail
    # todo ani
    ret = []
    is_slash = False
    #[value for value in b if any(d in value for d in a)]
    for r in rel_list:
        a = r.a # keep this around if we'd rather use the text
        href = a.get('href')
        if href not in canonical_tag_ids:
            print(href, 'not found in canonical tags, checking')
            # we need to find out if the tag is canonical so we can dedupe
            # build the url to check for redirect
            check_url = works_base_url.format(href)
            time.sleep(5)
            req = requests.get(check_url)
            if req.history and req.url != check_url:
                # then we did a redirect and the url where we ended should be canonical
                unfurled_url = urlparse(req.url).path
                canonical_tag_ids.add(unfurled_url)
                href = unfurled_url

            else:
                # we have the terimunus and a 200
                canonical_tag_ids.add(href)
        else:
            print(href, 'was in canonical tags, continue')

        href_decoded = unquote(href)
        # decode the hrefs to normalize tags
        if any(t in href_decoded for t in rel_tags):
            split = href_decoded.split('/')[2]
            pair_str = split.replace('*a*', '&').replace('*s*', '/')
            is_slash = '/' in pair_str
            ret.append(pair_str)
        else:
            # just append the text
            ret.append(a.text)


    print(canonical_tag_ids)
    return is_slash, ret


def _parse_ao3_result_list(html_str):
    """
    Uses beautiful soup to transform html into json with relevant metadata.
    Things I care about: title, author, id, rating, tags, pairings, description, warnings, 
    word count, chapters, kudos, hits, comments, date published, date updated
    """
    global unique_ids
    soup = BeautifulSoup(html_str, 'html.parser')
    work_index_group = soup.find('ol', class_="work index group")
    works = work_index_group.find_all('li', class_="work")

    jsons = []
    for work in works:
        # basics
        header = work.div
        h4 = header.h4
        link = h4.a
        author = link.find_next().text
        id_ = link.get('href')
        if id_ in unique_ids:
            continue # we already have it so we can keep going
        else:
            unique_ids.add(id_)
        title = link.string
        is_anon = False
        is_orphan = 'orphan_account' == author
        
        # logic gets screwed up b/c anonymous doesn't link
        # this is a hack, but orphan_account should just work since it links
        if 'Anonymous' in h4.text and 'Anonymous' not in title:
            is_anon = True
            author = 'Anonymous'

        # wrangle the required tags
        required_tags = header.find('ul', class_="required-tags")
        tag_lis = required_tags.find_all('li')
        rating = tag_lis[0].a.text
        warnings = tag_lis[1].a.text.split(', ')
        category = tag_lis[2].a.text.split(', ')
        is_wip = tag_lis[3].a.text == "Work in Progress"

        # unfortunately, this is the best date we can do from search
        last_updated = header.find('p', class_="datetime").text

        # wrangle all the tags
        tags_commas = work.find('ul', class_="tags commas")
        relationships = tags_commas.find_all('li', class_="relationships")
        is_slash = False
        if relationships:
            is_slash, relationships = _wrangle_relationship_tags(relationships)
        
        freeforms = tags_commas.find_all('li', class_="freeforms")
        if freeforms:
            freeforms = [f.a.text for f in freeforms]
        
        bq = work.find('blockquote', class_="userstuff summary")
        summary = bq.text if bq else ''  #evidently, you can have no summary      
        
        # gran series meta from summary and break it down
        series = work.find('ul', class_="series")
        is_series = False
        all_series = []
        if series:
            is_series = True
            series_ls = series.find_all('li')
            for s in series_ls:
                installment = int(s.strong.text.replace(',', '')) # wild if this is needed
                series_id = s.a.get('href')
                series_name = s.a.text
                series_meta = {
                    'installment': installment,
                    'seriesId': series_id,
                    'seriesName': series_name,
                }
                all_series.append(series_meta)

        stats_all = work.find('dl', class_="stats")
        language = stats_all.find('dd', class_="language").text
        words = _stat_parse_helper(stats_all, 'words')
        
        chapters = stats_all.find('dd', class_="chapters").text.split('/')
        cur_chapters = int(chapters[0].replace(',', ''))
        intended_chapters = chapters[1]
        
        # stats stuff
        kudos = _stat_parse_helper(stats_all, 'kudos')
        hits = _stat_parse_helper(stats_all, 'hits')
        comments = _stat_parse_helper(stats_all, 'comments')
        collections = _stat_parse_helper(stats_all, 'collections')
        # i have decided that i do not care about collection meta
        # but if i did, it would go here
        bookmarks = _stat_parse_helper(stats_all, 'bookmarks')

        # put that shit together
        jsons.append({
            "title": title,
            "author": author,
            "isAnon": is_anon,
            "isOrphan": is_orphan,
            "id": id_,
            "rating": rating,
            "warnings": warnings,
            "category": category,
            "isWip": is_wip,
            "lastUpdated": last_updated,
            "relationships": relationships,
            "isSlash": is_slash,
            "freeforms": freeforms,
            "summary": summary,
            "isSeries": is_series,
            "seriesMeta": all_series,
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
    # todo ani, make this page
    # r = requests.get(test_url_contains_anonymous)
    # html = r.text

    # result_list = _parse_ao3_result_list(html)
    result_list = process_ao3_loop()
    
    with open('outfile.json', 'w') as outfile:
        json.dump({'data': result_list}, outfile,indent=4)

if __name__ == "__main__":
    main()


# todo ani, commandline run logic with any search
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
